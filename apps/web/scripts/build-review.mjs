import { execFileSync } from "node:child_process";
import { build } from "esbuild";
import { cp, mkdir, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("../", import.meta.url));
const output = path.resolve(webRoot, "../../docs");
const buildOutput = path.join(webRoot, "dist");

// Build without an identifying hostname or a deployment-specific URL prefix.
execFileSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], {
  cwd: webRoot,
  stdio: "inherit",
  env: {
    ...process.env,
    ASTRO_TELEMETRY_DISABLED: "1",
    PUBLIC_BASE_PATH: "/",
    PUBLIC_SITE_URL: "https://example.invalid",
  },
});

// This directory contains generated review pages only.
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(buildOutput, output, { recursive: true });

async function htmlFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await htmlFiles(filename)));
    else if (entry.name.endsWith(".html")) files.push(filename);
  }
  return files;
}

// Anonymous GitHub serves pages with "Content-Security-Policy: sandbox" and no
// allow-same-origin. The page then has an opaque origin, so the browser blocks
// every ES module fetched from the server (a CORS error) and no island hydrates.
// Classic scripts are not subject to CORS, so all external modules become classic
// bundles. Islands look their modules up in a registry instead of importing them.
async function makeSandboxSafe(directory) {
  const assets = path.join(directory, "_astro");
  const pages = await htmlFiles(directory);
  const islandModules = new Set();
  for (const page of pages) {
    const html = await readFile(page, "utf8");
    for (const [, url] of html.matchAll(/\b(?:component|renderer)-url="([^"]+)"/g)) {
      islandModules.add(path.basename(url));
    }
  }

  const names = [...islandModules];
  await build({
    stdin: {
      contents: [
        ...names.map((name, index) => `import * as m${index} from ${JSON.stringify(`./${name}`)};`),
        `const modules = {${names.map((name, index) => `${JSON.stringify(name)}: m${index}`).join(", ")}};`,
        "window.__reviewImport = async (url) => {",
        '  const name = new URL(url, document.baseURI).pathname.split("/").pop();',
        '  if (!modules[name]) throw new Error(`Module missing from review bundle: ${name}`);',
        "  return modules[name];",
        "};",
      ].join("\n"),
      resolveDir: assets,
    },
    bundle: true,
    format: "iife",
    minify: true,
    outfile: path.join(assets, "review-islands.js"),
  });

  const pageScripts = new Set();
  for (const page of pages) {
    let html = await readFile(page, "utf8");
    const relativeToAssets = path.relative(path.dirname(page), assets).split(path.sep).join("/") || ".";
    if (html.includes("<astro-island")) {
      html = html.replace("</head>", `<script src="${relativeToAssets}/review-islands.js"></script></head>`);
      html = html.replace(/<script>[^<]*?astro-island[\s\S]*?<\/script>/g, (script) =>
        script.replace(/\bimport\(/g, "window.__reviewImport("),
      );
    }
    html = html.replace(/<script type="module" src="([^"]+)"([^>]*)><\/script>/g, (_, url, rest) => {
      pageScripts.add(path.basename(url));
      return `<script defer src="${url}"${rest}></script>`;
    });
    await writeFile(page, html);
  }

  for (const name of pageScripts) {
    const file = path.join(assets, name);
    await build({ entryPoints: [file], bundle: true, format: "iife", minify: true, outfile: file, allowOverwrite: true });
  }

  // Modules now inside the classic bundle are no longer requested by any page.
  const leftovers = (await readdir(assets)).filter(
    (name) => name.endsWith(".js") && name !== "review-islands.js" && !pageScripts.has(name),
  );
  await Promise.all(leftovers.map((name) => rm(path.join(assets, name))));
}

async function makePortable(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await makePortable(filename);
    } else if (entry.name.endsWith(".html")) {
      const original = await readFile(filename, "utf8");
      const references = [...original.matchAll(/\b(?:href|src|component-url|renderer-url)="(\/(?!\/)[^"]*)"/g)];
      const replacements = new Map();
      for (const [, url] of references) {
        const { pathname, search, hash } = new URL(url, "https://example.invalid");
        const target = path.join(output, decodeURIComponent(pathname));
        const targetInfo = await stat(target);
        let relative = path.relative(path.dirname(filename), target).split(path.sep).join("/");
        if (!relative.startsWith(".")) relative = `./${relative}`;
        if (targetInfo.isDirectory() && !relative.endsWith("/")) relative += "/";
        replacements.set(url, relative + search + hash);
      }
      const portable = original.replace(
        /\b(href|src|component-url|renderer-url)="(\/(?!\/)[^"]*)"/g,
        (_, attribute, url) => `${attribute}="${replacements.get(url)}"`,
      );
      await writeFile(filename, portable);
    }
  }
}

await makePortable(output);
await makeSandboxSafe(output);
// Preserve Astro's _astro directory when GitHub publishes from a branch.
await writeFile(path.join(output, ".nojekyll"), "");
console.log("Review website generated in docs/ with relative links.");
