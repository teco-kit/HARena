<script lang="ts">
  import datasetDetailsData from "../generated/dataset-details.json";
  import datasetPaperDetailsData from "../generated/dataset-paper-details.json";
  import modelDetailsData from "../generated/model-details.json";
  import paperLinks from "../generated/paper-links.json";
  import {
    getEntityMarker,
    getMarkerPath,
  } from "../lib/entityMarkers";

  type Dataset = {
    id: string;
    name: string;
  };
  type Model = {
    id: string;
    name: string;
    family: string;
    framework: string;
  };
  type Catalog = {
    datasets: Dataset[];
    models: Model[];
  };
  type Result = {
    model_id: string;
    dataset_id: string;
    split_id: string;
    status: string;
    metrics: Record<string, number | null>;
    window_size_seconds?: number;
    source?: {
      window_size_seconds?: number;
      [key: string]: unknown;
    };
  };
  type LeaderboardRow = Model & {
    netImprovement: number | null;
    netImprovementCi95: number | null;
    macroF1: number | null;
  };
  type McuStatus = "ok" | "no_fit_flash" | "no_fit_ram" | "failed" | null;
  type DeploymentRow = {
    model_id: string;
    dataset_id: string;
    window_size_seconds: number;
    phone_latency_ms: number | null;
    phone_memory_mb: number | null;
    phone_oom: boolean;
    watch_latency_ms: number | null;
    watch_memory_mb: number | null;
    watch_oom: boolean;
    mcu_status: McuStatus | string;
    mcu_latency_ms: number | null;
    mcu_ram_kb: number | null;
    mcu_flash_kb: number | null;
    mcu_energy_mj: number | null;
  };
  type DeploymentData = {
    source: { snapshot_date: string; reference_model: string; devices: Record<string, string> };
    rows: DeploymentRow[];
  };
  type DeviceId = "phone" | "watch" | "mcu";
  type CostKey = "latency" | "memory" | "flash" | "energy";
  type DeploymentMetric =
    | "phone_latency_ms"
    | "phone_memory_mb"
    | "watch_latency_ms"
    | "watch_memory_mb"
    | "mcu_latency_ms"
    | "mcu_ram_kb"
    | "mcu_flash_kb"
    | "mcu_energy_mj";
  type McuMetric = "mcu_latency_ms" | "mcu_ram_kb" | "mcu_flash_kb" | "mcu_energy_mj";
  type PaperLink = {
    title: string;
    url: string;
  };
  type ModelAuthor = {
    name: string;
    affiliation: string;
  };
  type DatasetPaperDetail = {
    institutions?: string[];
    authors?: ModelAuthor[];
  };
  type DatasetPaperDetailsData = {
    source: {
      note: string;
    };
    datasets: Record<string, DatasetPaperDetail>;
  };
  type ModelDetail = {
    params: string | null;
    macs: string | null;
    institutions: string[];
    authors: ModelAuthor[];
  };
  type ModelDetailsData = {
    source: {
      window_size_seconds: number;
    note: string;
    };
    models: Record<string, ModelDetail>;
  };
  type DatasetDetail = {
    year: number;
    subjects: number;
    activities: number;
    settings: string;
    deviceTypes: string;
    sensorModalities: string;
    channels: number;
  };
  type DatasetDetailsData = {
    source: {
      table: string;
      note: string;
      abbreviations: string;
    };
    datasets: Record<string, DatasetDetail>;
  };
  type SortKey =
    | "net_improvement"
    | "macro_f1"
    | `pareto:${DeploymentMetric}`;
  type SortDirection = "asc" | "desc";
  type ViewId = "leaderboard" | "best" | "matrix" | "deployment" | "gap" | "pareto";
  type ComponentMatchMode = "inclusive" | "exact";
  type ScatterScale = "log" | "linear";
  type ScatterMetric = DeploymentMetric;
  type ScatterConfig = {
    metric: ScatterMetric;
    title: string;
    xLabel: string;
    group: string;
    unit: string;
  };
  type ScatterPoint = {
    model_id: string;
    name: string;
    family: string;
    color: string;
    x: number;
    y: number;
    isPareto: boolean;
    dominators: string[];
  };
  type ScatterPlot = ScatterConfig & {
    scale: ScatterScale;
    points: ScatterPoint[];
    frontierPoints: ScatterPoint[];
    xMin: number;
    xMax: number;
    yMin: number;
    yMax: number;
    xTicks: number[];
    yTicks: number[];
    missingCount: number;
  };
  type FilterOption = {
    id: string;
    name: string;
    definition?: string;
  };
  type BestScoreKey =
    | "netImprovement"
    | "macroF1";

  let {
    catalog,
    defaultWindowSizeSeconds = 3,
    deployment,
    results,
  }: {
    catalog: Catalog;
    defaultWindowSizeSeconds?: number;
    deployment: DeploymentData;
    results: Result[];
  } = $props();

  // Abbreviations of the paper's model table.
  const familyShortLabels: Record<string, string> = {
    attn: "Attn",
    cnn: "CNN",
    dense: "Dense",
    fe: "FE",
    graph: "Graph",
    rnn: "RNN",
    spec: "Spec",
  };
  const familyPartsById: Record<string, string[]> = {
    attn_cnn_dense: ["attn", "cnn", "dense"],
    attn_cnn_dense_rnn: ["attn", "cnn", "dense", "rnn"],
    classical_ml: ["fe"],
    cnn: ["cnn"],
    cnn_dense_graph: ["cnn", "dense", "graph"],
    cnn_dense_rnn: ["cnn", "dense", "rnn"],
    compact_neural: ["attn", "cnn", "dense", "rnn"],
    dense: ["dense"],
    dense_rnn: ["dense", "rnn"],
    dense_spec: ["dense", "spec"],
    fe: ["fe"],
    neural: ["neural"],
  };
  const classicalBaselineIds = new Set(["knn", "random_forest", "svm"]);
  const classicalBaselineDetails: Record<string, string> = {
    knn: "k=5, distance-weighted",
    random_forest: "100 trees, depth=8",
    svm: "RBF kernel, C=1",
  };

  let selectedDatasetIds = $state(catalog.datasets.map((item) => item.id));
  let selectedModelFamilyIds = $state(getModelFamilyIds(catalog.models));
  let selectedModelIds = $state(catalog.models.map((item) => item.id));
  let selectedWindowSizeSeconds = $state(defaultWindowSizeSeconds);
  let componentMatchMode = $state<ComponentMatchMode>("inclusive");
  let selectedDetailModelId = $state<string | null>(null);
  let selectedDetailDatasetId = $state<string | null>(null);
  let activeView = $state<ViewId>("leaderboard");
  let selectedDevice = $state<DeviceId>("mcu");
  let matrixSelection = $state<"macro_f1" | CostKey>("macro_f1");
  let selectedCost = $state<CostKey>("latency");
  let scatterScale = $state<ScatterScale>("log");
  let showParetoFrontier = $state(true);
  let scatterTooltip = $state<{
    point: ScatterPoint;
    x: number;
    y: number;
  } | null>(null);
  let componentTooltip = $state<{
    text: string;
    x: number;
    y: number;
  } | null>(null);
  let sortKey = $state<SortKey>("macro_f1");
  let sortDirection = $state<SortDirection>("desc");

  const datasetDetails = datasetDetailsData as DatasetDetailsData;
  const datasetDetailMap = datasetDetails.datasets;
  const datasetPaperDetails = datasetPaperDetailsData as DatasetPaperDetailsData;
  const datasetPaperDetailMap = datasetPaperDetails.datasets;
  const modelDetails = modelDetailsData as ModelDetailsData;
  const detailMap = modelDetails.models;
  const linkMap = paperLinks as {
    datasets: Record<string, PaperLink>;
    models: Record<string, PaperLink>;
  };
  const bestBox = { width: 1100, height: 600, left: 76, right: 16, top: 66, bottom: 118 };
  const gapBox = { width: 1100, height: 520, left: 56, right: 16, top: 24, bottom: 118 };
  const plotBox = {
    width: 920,
    height: 500,
    left: 72,
    right: 30,
    top: 30,
    bottom: 64,
  };
  const deploymentMetricConfigs: Array<{
    metric: DeploymentMetric;
    group: string;
    label: string;
    unit: string;
  }> = [
    { metric: "phone_latency_ms", group: "Phone", label: "Latency", unit: "ms" },
    { metric: "phone_memory_mb", group: "Phone", label: "Peak memory overhead", unit: "MB" },
    { metric: "watch_latency_ms", group: "Watch", label: "Latency", unit: "ms" },
    { metric: "watch_memory_mb", group: "Watch", label: "Peak memory overhead", unit: "MB" },
    { metric: "mcu_latency_ms", group: "MCU", label: "Latency", unit: "ms" },
    { metric: "mcu_ram_kb", group: "MCU", label: "Peak RAM", unit: "KB" },
    { metric: "mcu_flash_kb", group: "MCU", label: "Flash", unit: "KB" },
    { metric: "mcu_energy_mj", group: "MCU", label: "Energy per inference", unit: "mJ" },
  ];
  const deviceCosts: Record<DeviceId, Array<{ key: CostKey; label: string; metric: DeploymentMetric }>> = {
    phone: [
      { key: "latency", label: "Latency", metric: "phone_latency_ms" },
      { key: "memory", label: "Peak Memory Overhead", metric: "phone_memory_mb" },
    ],
    watch: [
      { key: "latency", label: "Latency", metric: "watch_latency_ms" },
      { key: "memory", label: "Peak Memory Overhead", metric: "watch_memory_mb" },
    ],
    mcu: [
      { key: "latency", label: "Latency", metric: "mcu_latency_ms" },
      { key: "memory", label: "Peak RAM", metric: "mcu_ram_kb" },
      { key: "flash", label: "Flash", metric: "mcu_flash_kb" },
      { key: "energy", label: "Energy", metric: "mcu_energy_mj" },
    ],
  };
  const deploymentGroups = ["Phone", "Watch", "MCU"];
  const referenceModelId = deployment.source.reference_model;
  const referenceModelName =
    catalog.models.find((model) => model.id === referenceModelId)?.name ?? referenceModelId;
  const mcuMinFits = 10;
  const deploymentIndex = new Map(
    deployment.rows.map((row) => [
      `${row.window_size_seconds}|${row.dataset_id}|${row.model_id}`,
      row,
    ]),
  );
  const scatterConfigs: ScatterConfig[] = deploymentMetricConfigs.map((config) => {
    const isMcu = config.group === "MCU";
    const label = isMcu
      ? `${config.label} relative to ${referenceModelName}`
      : `Mean ${config.label.toLowerCase()} (${config.unit})`;
    return {
      metric: config.metric,
      group: config.group,
      unit: isMcu ? `× ${referenceModelName}` : config.unit,
      title: `${config.group}: Macro-F1 vs. ${config.label}`,
      xLabel: label,
    };
  });
  const numberFormatter = new Intl.NumberFormat("en-US");
  const metricInfo = {
    netImprovement:
      "Selection-dependent. For each selected dataset, subtracts the best classical baseline Test Macro-F1 from this model’s Test Macro-F1, then averages those differences. The interval is a 95% confidence interval across datasets; higher is better.",
    macroF1:
      "Performance for the selected window length. Arithmetic mean of stored Test Macro-F1 values across all benchmark datasets, with equal weight per dataset. Dataset, model, and building block filters only control visibility; higher is better.",
    pareto:
      "Share of the selected datasets on which this model lies on the Pareto front of Test Macro-F1 against this cost on the selected device: no other model is both more accurate and cheaper on that dataset. All models compete regardless of the model filters; on the MCU only models that fit compete. Higher is better.",
  };

  const completeResults = $derived(
    results.filter((result) => result.status === "complete" || result.status === "example"),
  );
  const windowSizeOptions = $derived(
    [...new Set(completeResults.map(resultWindowSizeSeconds))].sort((a, b) => a - b),
  );
  const validResults = $derived(
    completeResults.filter(
      (result) => resultWindowSizeSeconds(result) === selectedWindowSizeSeconds,
    ),
  );
  const selectedDatasetSet = $derived(new Set(selectedDatasetIds));
  const selectedDatasets = $derived(
    catalog.datasets.filter((item) => selectedDatasetSet.has(item.id)),
  );
  const selectedModelFamilySet = $derived(new Set(selectedModelFamilyIds));
  const selectedModelSet = $derived(new Set(selectedModelIds));
  const datasetFilterOptions = $derived(
    [...catalog.datasets].sort((a, b) => compareLabels(a.name, b.name)),
  );
  const modelFilterOptions = $derived(
    catalog.models
      .map((item) => ({ ...item, name: modelDisplayName(item.id, item.name) }))
      .sort((a, b) => compareLabels(a.name, b.name)),
  );
  const modelFamilyOptions = $derived(getModelFamilyOptions(catalog.models));
  const selectedDatasetSummary = $derived(formatSelectedDatasetSummary());
  const selectedModelFamilySummary = $derived(formatSelectedModelFamilySummary());
  const selectedModelSummary = $derived(formatSelectedModelSummary());
  const selectedDetailModel = $derived(
    selectedDetailModelId
      ? (() => {
          const model = catalog.models.find((item) => item.id === selectedDetailModelId);
          return model ? { ...model, name: modelDisplayName(model.id, model.name) } : null;
        })()
      : null,
  );
  const selectedDetail = $derived(
    selectedDetailModelId ? getModelDetail(selectedDetailModelId) : null,
  );
  const selectedDetailDataset = $derived(
    selectedDetailDatasetId
      ? catalog.datasets.find((item) => item.id === selectedDetailDatasetId) ?? null
      : null,
  );
  const selectedDatasetDetail = $derived(
    selectedDetailDatasetId ? getDatasetDetail(selectedDetailDatasetId) : null,
  );
  const selectedDatasetPaperDetail = $derived(
    selectedDetailDatasetId ? datasetPaperDetailMap[selectedDetailDatasetId] ?? null : null,
  );
  const visibleModels = $derived(
    catalog.models.filter(
      (item) => selectedModelSet.has(item.id) && isFamilyAllowed(item.family),
    ).map((item) => ({ ...item, name: modelDisplayName(item.id, item.name) })),
  );
  const activeCosts = $derived(deviceCosts[selectedDevice]);
  const activeCost = $derived(
    activeCosts.find((cost) => cost.key === selectedCost) ?? activeCosts[0],
  );
  const activeScatterMetric = $derived(activeCost.metric);
  const macroF1ByCase = $derived(
    new Map(
      validResults.flatMap((result) =>
        typeof result.metrics.macro_f1 === "number"
          ? [[`${result.dataset_id}|${result.model_id}`, result.metrics.macro_f1] as const]
          : [],
      ),
    ),
  );
  const paretoFronts = $derived(computeParetoFronts());
  const benchmarkRows = $derived(
      catalog.models.map((model) => {
        return {
          ...model,
          name: modelDisplayName(model.id, model.name),
          netImprovement: null,
          netImprovementCi95: null,
          macroF1: meanMacroF1AcrossDatasets(model.id),
        };
      }),
  );

  const rows = $derived(
    benchmarkRows
      .filter((row) => selectedModelSet.has(row.id) && isFamilyAllowed(row.family))
      .map((row) => {
        const improvement = netImprovementStats(row.id);
        return {
          ...row,
          netImprovement: improvement.mean,
          netImprovementCi95: improvement.ci95,
        };
      })
      .sort(compareRows),
  );

  const bestScores = $derived({
    netImprovement: bestScoreValue(rows, "netImprovement", "desc"),
    macroF1: bestScoreValue(rows, "macroF1", "desc"),
  });
  const bestParetoShares = $derived(
    new Map(
      activeCosts.map((cost) => [
        cost.metric,
        Math.max(0, ...rows.map((row) => paretoShare(row.id, cost.metric) ?? 0)),
      ]),
    ),
  );
  const paretoMatrixDatasets = $derived(
    [...selectedDatasets]
      .map((dataset) => ({
        ...dataset,
        meanF1: averageAvailable(catalog.models.map((model) => modelMacroF1(model.id, dataset.id))) ?? 0,
      }))
      .sort((a, b) => b.meanF1 - a.meanF1),
  );
  const paretoMatrixRows = $derived(
    visibleModels
      .map((model) => ({
        id: model.id,
        name: model.name,
        share: paretoShare(model.id, activeScatterMetric),
      }))
      .sort((a, b) => (b.share ?? -1) - (a.share ?? -1)),
  );
  const selectedDetailRow = $derived(rows.find((row) => row.id === selectedDetailModelId) ?? null);
  const netImprovementScale = $derived(getNetImprovementScale(rows));
  const activeScatterConfig = $derived(
    scatterConfigs.find((config) => config.metric === activeScatterMetric) ?? scatterConfigs[0],
  );
  const scatterPlot = $derived(createScatterPlot(activeScatterConfig, scatterScale));
  const scatterLabels = $derived(placeScatterLabels(scatterPlot));
  const scatterLegend = $derived([...scatterPlot.points].sort((a, b) => b.y - a.y));
  const matrixMetric = $derived<"macro_f1" | DeploymentMetric>(
    matrixSelection === "macro_f1"
      ? "macro_f1"
      : (activeCosts.find((cost) => cost.key === matrixSelection) ?? activeCosts[0]).metric,
  );
  const matrixSelectValue = $derived(
    matrixSelection === "macro_f1"
      ? "macro_f1"
      : (activeCosts.find((cost) => cost.key === matrixSelection) ?? activeCosts[0]).key,
  );
  const deviceLabel = $derived(
    selectedDevice === "mcu" ? "MCU" : selectedDevice === "phone" ? "Phone" : "Watch",
  );
  const deviceFilterApplies = $derived(activeView !== "deployment" && activeView !== "gap" && activeView !== "best");
  const matrixConfig = $derived(
    matrixMetric === "macro_f1"
      ? null
      : (deploymentMetricConfigs.find((config) => config.metric === matrixMetric) ?? null),
  );
  // Models fit different MCU datasets, so absolute MCU means are not comparable.
  const showMatrixMeans = $derived(matrixMetric === "macro_f1" || !isMcuMetric(matrixMetric));
  const matrixRows = $derived(
    selectedDatasets.map((item) => {
      const cells = visibleModels.map((model) =>
        matrixMetric === "macro_f1"
          ? {
              modelId: model.id,
              modelName: model.name,
              value: modelMacroF1(model.id, item.id),
              flag: null as string | null,
              reason: "No result",
            }
          : deploymentCell(model.id, model.name, item.id, matrixMetric),
      );
      const positive = cells.flatMap((cell) =>
        cell.value !== null && cell.value > 0 ? [cell.value] : [],
      );

      return {
        ...item,
        cells,
        mean: averageAvailable(cells.map((cell) => cell.value)),
        min: positive.length ? Math.min(...positive) : null,
        max: positive.length ? Math.max(...positive) : null,
      };
    }),
  );
  const matrixColumnMeans = $derived(
    visibleModels.map((model, modelIndex) => ({
      modelId: model.id,
      modelName: model.name,
      value: averageAvailable(matrixRows.map((row) => row.cells[modelIndex]?.value ?? null)),
    })),
  );
  const matrixGrandMean = $derived(
    averageAvailable(matrixRows.flatMap((row) => row.cells.map((cell) => cell.value))),
  );
  const deploymentSummaryRows = $derived(
    visibleModels
      .map((model) => ({
        id: model.id,
        name: model.name,
        macroF1: selectedMeanMacroF1(model.id),
        phoneLatency: deviceMean(model.id, "phone_latency_ms"),
        phoneMemory: deviceMean(model.id, "phone_memory_mb"),
        watchLatency: deviceMean(model.id, "watch_latency_ms"),
        watchMemory: deviceMean(model.id, "watch_memory_mb"),
        fits: mcuFitCount(model.id),
        mcuLatency: mcuRelativeCost(model.id, "mcu_latency_ms"),
        mcuRam: mcuRelativeCost(model.id, "mcu_ram_kb"),
        mcuFlash: mcuRelativeCost(model.id, "mcu_flash_kb"),
        mcuEnergy: mcuRelativeCost(model.id, "mcu_energy_mj"),
      }))
      .sort((a, b) => (b.macroF1 ?? -1) - (a.macroF1 ?? -1)),
  );
  const deploymentSummaryBest = $derived({
    phoneLatency: minOf(deploymentSummaryRows.map((row) => row.phoneLatency)),
    phoneMemory: minOf(deploymentSummaryRows.map((row) => row.phoneMemory)),
    watchLatency: minOf(deploymentSummaryRows.map((row) => row.watchLatency)),
    watchMemory: minOf(deploymentSummaryRows.map((row) => row.watchMemory)),
    mcuLatency: minOf(deploymentSummaryRows.filter((row) => row.fits >= mcuMinFits).map((row) => row.mcuLatency)),
    mcuRam: minOf(deploymentSummaryRows.filter((row) => row.fits >= mcuMinFits).map((row) => row.mcuRam)),
    mcuFlash: minOf(deploymentSummaryRows.filter((row) => row.fits >= mcuMinFits).map((row) => row.mcuFlash)),
    mcuEnergy: minOf(deploymentSummaryRows.filter((row) => row.fits >= mcuMinFits).map((row) => row.mcuEnergy)),
  });
  const deploymentExtents = $derived(
    Object.fromEntries(
      (["phoneLatency", "phoneMemory", "watchLatency", "watchMemory", "mcuLatency", "mcuRam", "mcuFlash", "mcuEnergy"] as const).map((key) => {
        const values = deploymentSummaryRows.flatMap((row) => {
          const value = row[key];
          return value !== null && value > 0 ? [value] : [];
        });
        return [key, { min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null }];
      }),
    ) as Record<string, { min: number | null; max: number | null }>,
  );
  // The best model on a dataset is taken over all models, so hiding models does not change a gap.
  const bestGapColumns = $derived(
    visibleModels
      .map((model) => {
        const points = selectedDatasets.flatMap((dataset) => {
          const score = modelMacroF1(model.id, dataset.id);
          if (score === null) return [];
          const best = Math.max(
            ...catalog.models.flatMap((other) => {
              const value = modelMacroF1(other.id, dataset.id);
              return value === null ? [] : [value];
            }),
          );
          return [{ datasetId: dataset.id, name: dataset.name, gap: (best - score) * 100, score, best }];
        });
        const gaps = points.map((point) => point.gap);
        const mean = gaps.length ? averageValues(gaps) : 0;
        return {
          id: model.id,
          name: classicalBaselineIds.has(model.id) ? `${model.name} (cl.)` : model.name,
          points,
          mean,
          std: gaps.length > 1 ? sampleStandardDeviation(gaps, mean) : 0,
          wins: points.filter((point) => point.score === point.best).length,
          meanF1: averageAvailable(points.map((point) => point.score)),
        };
      })
      .filter((column) => column.points.length > 0)
      .sort((a, b) => (b.meanF1 ?? 0) - (a.meanF1 ?? 0)),
  );
  const bestYMax = $derived(
    Math.max(10, Math.ceil(Math.max(0, ...bestGapColumns.flatMap((c) => c.points.map((p) => p.gap))) / 10) * 10),
  );
  const bestTicks = $derived(
    Array.from({ length: Math.round(bestYMax / 10) + 1 }, (_, index) => index * 10),
  );
  const gapColumns = $derived(
    selectedDatasets
      .map((dataset) => {
        const points = visibleModels.flatMap((model) => {
          const result = validResults.find(
            (item) => item.dataset_id === dataset.id && item.model_id === model.id,
          );
          const test = result?.metrics.macro_f1;
          const val = result?.metrics.val_macro_f1;
          if (typeof test !== "number" || typeof val !== "number") return [];
          return [{ modelId: model.id, name: model.name, gap: (val - test) * 100, val, test }];
        });
        const gaps = points.map((point) => point.gap);
        const mean = gaps.length ? averageValues(gaps) : 0;
        return {
          id: dataset.id,
          name: dataset.name,
          subjects: datasetDetailMap[dataset.id]?.subjects ?? null,
          points,
          mean,
          std: gaps.length > 1 ? sampleStandardDeviation(gaps, mean) : 0,
        };
      })
      .filter((column) => column.points.length > 0)
      .sort((a, b) => b.mean - a.mean),
  );
  const gapYMin = $derived(
    Math.min(0, Math.floor(Math.min(0, ...gapColumns.flatMap((c) => c.points.map((p) => p.gap))) / 10) * 10),
  );
  const gapYMax = $derived(
    Math.max(10, Math.ceil(Math.max(0, ...gapColumns.flatMap((c) => c.points.map((p) => p.gap))) / 10) * 10),
  );
  const gapTicks = $derived(
    Array.from({ length: Math.round((gapYMax - gapYMin) / 10) + 1 }, (_, index) => gapYMin + index * 10),
  );

  function averageMetric(items: Result[], metric: string) {
    const values = items
      .map((result) => result.metrics[metric])
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));

    if (values.length === 0) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function resultWindowSizeSeconds(result: Result) {
    return result.window_size_seconds ?? result.source?.window_size_seconds ?? defaultWindowSizeSeconds;
  }

  function formatWindowSize(seconds: number) {
    return `${numberFormatter.format(seconds)} s`;
  }

  function compareByPerformanceRank(a: LeaderboardRow, b: LeaderboardRow) {
    const byMacroF1 = compareNullableNumber(a.macroF1, b.macroF1, "desc");
    if (byMacroF1 !== 0) return byMacroF1;
    return a.id.localeCompare(b.id);
  }

  function compareRows(a: LeaderboardRow, b: LeaderboardRow) {
    let comparison = 0;

    if (sortKey === "macro_f1") {
      comparison = compareNullableNumber(a.macroF1, b.macroF1, sortDirection);
    } else if (sortKey === "net_improvement") {
      comparison = compareNullableNumber(a.netImprovement, b.netImprovement, sortDirection);
    } else {
      const metric = sortKey.slice("pareto:".length) as DeploymentMetric;
      comparison = compareNullableNumber(paretoShare(a.id, metric), paretoShare(b.id, metric), sortDirection);
    }

    if (comparison !== 0) return comparison;
    return compareByPerformanceRank(a, b);
  }

  function compareNullableNumber(
    a: number | null,
    b: number | null,
    direction: SortDirection,
  ) {
    if (a === null && b === null) return 0;
    if (a === null) return 1;
    if (b === null) return -1;
    return direction === "asc" ? a - b : b - a;
  }

  function compareLabels(a: string, b: string) {
    return a.localeCompare(b, "en", { sensitivity: "base" });
  }

  function bestScoreValue(
    items: LeaderboardRow[],
    key: BestScoreKey,
    direction: SortDirection,
  ) {
    const values = items
      .map((item) => item[key])
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));

    if (values.length === 0) return null;
    return direction === "asc" ? Math.min(...values) : Math.max(...values);
  }

  function isBestScore(row: LeaderboardRow, key: BestScoreKey) {
    const value = row[key];
    const bestValue = bestScores[key];
    if (typeof value !== "number" || typeof bestValue !== "number") return false;
    return Math.abs(value - bestValue) < 1e-9;
  }

  function setSort(nextKey: SortKey) {
    if (sortKey === nextKey) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
      return;
    }

    sortKey = nextKey;
    sortDirection = defaultDirection();
  }

  function defaultDirection(): SortDirection {
    return "desc";
  }

  function netImprovementStats(modelId: string) {
    const deltas = catalog.datasets
      .filter((item) => selectedDatasetSet.has(item.id))
      .map((dataset) => {
        const modelScore = averageMetric(
          validResults.filter(
            (result) => result.dataset_id === dataset.id && result.model_id === modelId,
          ),
          "macro_f1",
        );
        const baselineScore = bestClassicalMacroF1(dataset.id);

        if (modelScore === null || baselineScore === null) return null;
        return modelScore - baselineScore;
      })
      .filter((value): value is number => value !== null);

    if (deltas.length === 0) {
      return { mean: null, ci95: null };
    }

    const mean = averageValues(deltas);
    const ci95 =
      deltas.length > 1 ? 1.96 * sampleStandardDeviation(deltas, mean) / Math.sqrt(deltas.length) : 0;

    return { mean, ci95 };
  }

  function bestClassicalMacroF1(datasetId: string) {
    const scores = catalog.models
      .filter((model) => classicalBaselineIds.has(model.id))
      .map((model) =>
        averageMetric(
          validResults.filter(
            (result) => result.dataset_id === datasetId && result.model_id === model.id,
          ),
          "macro_f1",
        ),
      )
      .filter((value): value is number => value !== null);

    if (scores.length === 0) return null;
    return Math.max(...scores);
  }

  function averageValues(values: number[]) {
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function averageAvailable(values: Array<number | null>) {
    const available = values.filter((value): value is number => value !== null);
    return available.length > 0 ? averageValues(available) : null;
  }

  function meanMacroF1AcrossDatasets(modelId: string) {
    const datasetScores = catalog.datasets
      .map((dataset) =>
        averageMetric(
          validResults.filter(
            (result) => result.model_id === modelId && result.dataset_id === dataset.id,
          ),
          "macro_f1",
        ),
      )
      .filter((value): value is number => value !== null);

    return datasetScores.length > 0 ? averageValues(datasetScores) : null;
  }

  function sampleStandardDeviation(values: number[], mean = averageValues(values)) {
    if (values.length < 2) return 0;
    const variance =
      values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1);
    return Math.sqrt(variance);
  }

  function getNetImprovementScale(items: LeaderboardRow[]) {
    const extents = items
      .flatMap((item) => {
        if (item.netImprovement === null) return [];
        const ci = item.netImprovementCi95 ?? 0;
        return [item.netImprovement - ci, item.netImprovement + ci, item.netImprovement];
      })
      .map(Math.abs);

    if (extents.length === 0) return 0.01;
    return Math.max(0.01, ...extents);
  }

  function sortAria(key: SortKey) {
    if (sortKey !== key) return "none";
    return sortDirection === "asc" ? "ascending" : "descending";
  }

  function formatSelectedDatasetSummary() {
    if (selectedDatasetIds.length === catalog.datasets.length) return "All datasets";
    if (selectedDatasetIds.length === 0) return "No datasets";
    if (selectedDatasetIds.length === 1) {
      return (
        catalog.datasets.find((item) => item.id === selectedDatasetIds[0])?.name ??
        "1 dataset"
      );
    }
    return `${selectedDatasetIds.length} datasets`;
  }

  function formatSelectedModelFamilySummary() {
    if (selectedModelFamilyIds.length === modelFamilyOptions.length) return "All building blocks";
    if (selectedModelFamilyIds.length === 0) return "No building blocks";
    if (selectedModelFamilyIds.length === 1) {
      return `${formatFamily(selectedModelFamilyIds[0])}${componentMatchMode === "exact" ? " · exact" : ""}`;
    }
    return `${selectedModelFamilyIds.length} components${componentMatchMode === "exact" ? " · exact" : ""}`;
  }

  function formatSelectedModelSummary() {
    if (selectedModelIds.length === catalog.models.length) return "All models";
    if (selectedModelIds.length === 0) return "No models";
    if (selectedModelIds.length === 1) {
      const model = catalog.models.find((item) => item.id === selectedModelIds[0]);
      return model ? modelDisplayName(model.id, model.name) : "1 model";
    }
    return `${selectedModelIds.length} models`;
  }

  function isDatasetSelected(id: string) {
    return selectedDatasetSet.has(id);
  }

  function isModelSelected(id: string) {
    return selectedModelSet.has(id);
  }

  function isModelFamilySelected(id: string) {
    return selectedModelFamilySet.has(id);
  }

  function toggleDataset(id: string) {
    if (selectedDatasetSet.has(id)) {
      selectedDatasetIds = selectedDatasetIds.filter((item) => item !== id);
      return;
    }

    selectedDatasetIds = [...selectedDatasetIds, id];
  }

  function toggleModelFamily(id: string) {
    if (selectedModelFamilySet.has(id)) {
      selectedModelFamilyIds = selectedModelFamilyIds.filter((item) => item !== id);
      return;
    }

    selectedModelFamilyIds = [...selectedModelFamilyIds, id];
  }

  function toggleModel(id: string) {
    if (selectedModelSet.has(id)) {
      selectedModelIds = selectedModelIds.filter((item) => item !== id);
      return;
    }

    selectedModelIds = [...selectedModelIds, id];
  }

  function selectAllModelFamilies() {
    selectedModelFamilyIds = modelFamilyOptions.map((item) => item.id);
  }

  function clearModelFamilies() {
    selectedModelFamilyIds = [];
  }

  function selectAllDatasets() {
    selectedDatasetIds = catalog.datasets.map((item) => item.id);
  }

  function clearDatasets() {
    selectedDatasetIds = [];
  }

  function selectAllModels() {
    selectedModelIds = catalog.models.map((item) => item.id);
  }

  function clearModels() {
    selectedModelIds = [];
  }

  function resetAllFilters() {
    selectedDatasetIds = catalog.datasets.map((item) => item.id);
    selectedModelIds = catalog.models.map((item) => item.id);
    selectedModelFamilyIds = getModelFamilyIds(catalog.models);
    selectedWindowSizeSeconds = defaultWindowSizeSeconds;
    selectedDevice = "mcu";
    componentMatchMode = "inclusive";
  }

  function selectTopDatasets() {
    selectedDatasetIds = catalog.datasets.slice(0, 10).map((item) => item.id);
  }

  function selectTopModels() {
    selectedModelIds = benchmarkRows
      .filter((model) => isFamilyAllowed(model.family))
      .sort(compareByPerformanceRank)
      .slice(0, 10)
      .map((model) => model.id);
  }

  function deploymentRow(modelId: string, datasetId: string) {
    return deploymentIndex.get(`${selectedWindowSizeSeconds}|${datasetId}|${modelId}`) ?? null;
  }

  function modelMacroF1(modelId: string, datasetId: string) {
    return macroF1ByCase.get(`${datasetId}|${modelId}`) ?? null;
  }

  /** Per cost and dataset, the models no other model beats on both Macro-F1 and cost. */
  function computeParetoFronts() {
    const fronts = new Map<DeploymentMetric, Map<string, Set<string>>>();
    for (const { metric } of deploymentMetricConfigs) {
      const byDataset = new Map<string, Set<string>>();
      for (const dataset of catalog.datasets) {
        const points = catalog.models
          .flatMap((model) => {
            const row = deploymentRow(model.id, dataset.id);
            const cost = row?.[metric] ?? null;
            const f1 = modelMacroF1(model.id, dataset.id);
            if (cost === null || f1 === null) return [];
            if (isMcuMetric(metric) && row?.mcu_status !== "ok") return [];
            return [{ id: model.id, cost, f1 }];
          })
          .sort((a, b) => a.cost - b.cost || b.f1 - a.f1);
        const front = new Set<string>();
        let best = -Infinity;
        for (const point of points) {
          if (point.f1 > best) {
            front.add(point.id);
            best = point.f1;
          }
        }
        byDataset.set(dataset.id, front);
      }
      fronts.set(metric, byDataset);
    }
    return fronts;
  }

  function isOnParetoFront(modelId: string, datasetId: string, metric: DeploymentMetric) {
    return paretoFronts.get(metric)?.get(datasetId)?.has(modelId) ?? false;
  }

  function paretoShare(modelId: string, metric: DeploymentMetric) {
    if (selectedDatasets.length === 0) return null;
    const hits = selectedDatasets.filter((dataset) => isOnParetoFront(modelId, dataset.id, metric));
    return hits.length / selectedDatasets.length;
  }

  function setDeviceSort() {
    if (sortKey.startsWith("pareto:")) sortKey = "macro_f1";
  }

  function selectedMeanMacroF1(modelId: string) {
    return averageAvailable(
      selectedDatasets.map((dataset) =>
        averageMetric(
          validResults.filter(
            (result) => result.model_id === modelId && result.dataset_id === dataset.id,
          ),
          "macro_f1",
        ),
      ),
    );
  }

  function deviceMean(modelId: string, metric: DeploymentMetric) {
    return averageAvailable(
      selectedDatasets.map((dataset) => deploymentRow(modelId, dataset.id)?.[metric] ?? null),
    );
  }

  function mcuFitCount(modelId: string) {
    return selectedDatasets.filter(
      (dataset) => deploymentRow(modelId, dataset.id)?.mcu_status === "ok",
    ).length;
  }

  /** Geometric mean of the cost ratio to the reference model, on datasets where both fit. */
  function mcuRelativeCost(modelId: string, metric: McuMetric) {
    const logs = selectedDatasets.flatMap((dataset) => {
      const row = deploymentRow(modelId, dataset.id);
      const reference = deploymentRow(referenceModelId, dataset.id);
      if (row?.mcu_status !== "ok" || reference?.mcu_status !== "ok") return [];
      const value = row[metric];
      const base = reference[metric];
      return value !== null && base !== null && value > 0 && base > 0
        ? [Math.log(value / base)]
        : [];
    });
    return logs.length ? Math.exp(averageValues(logs)) : null;
  }

  function isMcuMetric(metric: DeploymentMetric): metric is McuMetric {
    return metric.startsWith("mcu_");
  }

  function minOf(values: Array<number | null>) {
    const present = values.filter((value): value is number => value !== null);
    return present.length ? Math.min(...present) : null;
  }

  function deploymentCell(
    modelId: string,
    modelName: string,
    datasetId: string,
    metric: DeploymentMetric,
  ) {
    const row = deploymentRow(modelId, datasetId);
    let flag: string | null = null;
    let reason = "No measurement";
    if (row && metric.startsWith("phone_") && row.phone_oom) {
      flag = "M";
      reason = "Out of memory on the phone";
    } else if (row && metric.startsWith("watch_") && row.watch_oom) {
      flag = "M";
      reason = "Out of memory on the watch";
    } else if (row && isMcuMetric(metric) && row.mcu_status !== "ok" && !(metric === "mcu_flash_kb" && row.mcu_flash_kb !== null)) {
      if (row.mcu_status === "no_fit_flash") {
        flag = "F";
        reason = "Exceeds the MCU flash";
      } else if (row.mcu_status === "no_fit_ram") {
        flag = "R";
        reason = "Exceeds the MCU RAM";
      } else if (row.mcu_status === "failed") {
        flag = "E";
        reason = "Export or execution failed";
      }
    }
    return { modelId, modelName, value: flag ? null : (row?.[metric] ?? null), flag, reason };
  }

  function deploymentCellStyle(value: number | null, min: number | null, max: number | null) {
    if (value === null || value <= 0 || min === null || max === null) return "";
    if (max <= min) return scoreStyle(1);
    return scoreStyle(1 - (Math.log(value) - Math.log(min)) / (Math.log(max) - Math.log(min)));
  }

  function formatMatrixValue(value: number | null) {
    if (value === null) return "—";
    return matrixMetric === "macro_f1" ? formatMatrixScore(value) : formatCost(value);
  }

  function matrixValueLabel(value: number | null) {
    if (value === null) return "—";
    return matrixConfig ? `${formatCost(value)} ${matrixConfig.unit}` : formatPercent(value);
  }

  function formatCost(value: number | null) {
    if (value === null) return "-";
    if (value >= 1000) return numberFormatter.format(Math.round(value));
    if (value >= 100) return value.toFixed(0);
    if (value >= 10) return value.toFixed(1);
    return value.toFixed(2);
  }

  function bestX(index: number) {
    const inner = bestBox.width - bestBox.left - bestBox.right;
    return bestBox.left + (inner * (index + 0.5)) / Math.max(bestGapColumns.length, 1);
  }

  function bestY(value: number) {
    const inner = bestBox.height - bestBox.top - bestBox.bottom;
    return bestBox.top + inner * (1 - value / bestYMax);
  }

  /** Stable horizontal offset per dataset, so dots with similar gaps stay visible. */
  function bestJitter(datasetId: string) {
    const index = catalog.datasets.findIndex((dataset) => dataset.id === datasetId);
    return ((index + 0.5) / catalog.datasets.length - 0.5) * 26;
  }

  function gapX(index: number) {
    const inner = gapBox.width - gapBox.left - gapBox.right;
    return gapBox.left + (inner * (index + 0.5)) / Math.max(gapColumns.length, 1);
  }

  function gapY(value: number) {
    const inner = gapBox.height - gapBox.top - gapBox.bottom;
    return gapBox.top + inner * (1 - (value - gapYMin) / (gapYMax - gapYMin));
  }

  /** Stable horizontal offset per model, so dots with similar gaps stay visible. */
  function gapJitter(modelId: string) {
    const index = catalog.models.findIndex((model) => model.id === modelId);
    return ((index + 0.5) / catalog.models.length - 0.5) * 18;
  }

  function normalize(value: number, min: number, max: number, fallback: number) {
    if (max === min) return fallback;
    return (value - min) / (max - min);
  }

  function formatPercent(score: number | null) {
    if (score === null) return "pending";
    return `${(score * 100).toFixed(1)}%`;
  }

  function formatNetImprovement(score: number | null) {
    if (score === null) return "pending";
    return `${(score * 100).toFixed(2)}%`;
  }

  function formatNetImprovementCi(score: number | null) {
    if (score === null) return "pending";
    return `±${(score * 100).toFixed(2)}%`;
  }

  function netDirection(score: number | null) {
    if (score === null || score === 0) return "flat";
    return score > 0 ? "up" : "down";
  }

  function netBarStyle(row: LeaderboardRow) {
    if (row.netImprovement === null) return "";

    const ci = row.netImprovementCi95 ?? 0;
    const zero = 50;
    const value = netBarPercent(row.netImprovement);
    const ciLow = netBarPercent(row.netImprovement - ci);
    const ciHigh = netBarPercent(row.netImprovement + ci);
    const fillLeft = Math.min(zero, value);
    const fillWidth = Math.abs(value - zero);
    const ciLeft = Math.min(ciLow, ciHigh);
    const ciWidth = Math.abs(ciHigh - ciLow);

    return [
      `--net-fill-left: ${fillLeft.toFixed(2)}%;`,
      `--net-fill-width: ${fillWidth.toFixed(2)}%;`,
      `--net-ci-left: ${ciLeft.toFixed(2)}%;`,
      `--net-ci-width: ${Math.max(ciWidth, 0.8).toFixed(2)}%;`,
      `--net-ci-low: ${ciLow.toFixed(2)}%;`,
      `--net-ci-high: ${ciHigh.toFixed(2)}%;`,
    ].join(" ");
  }

  function netBarPercent(value: number) {
    if (netImprovementScale <= 0) return 50;
    const clamped = Math.max(-netImprovementScale, Math.min(netImprovementScale, value));
    return 50 + (clamped / netImprovementScale) * 50;
  }

  function formatCompactPercent(score: number | null) {
    if (score === null) return "—";
    return `${(score * 100).toFixed(1)}%`;
  }

  function formatMatrixScore(score: number | null) {
    if (score === null) return "—";
    return (score * 100).toFixed(1);
  }


  function formatModelSize(size: number | null) {
    if (size === null) return "";
    return `${size < 1 ? size.toFixed(2) : size.toFixed(1)} MB`;
  }

  function formatMemory(size: number | null) {
    if (size === null) return "";
    return `${size < 10 ? size.toFixed(2) : size.toFixed(1)} MB`;
  }

  function formatLatency(latency: number | null) {
    if (latency === null) return "";
    return `${latency < 10 ? latency.toFixed(2) : latency.toFixed(1)} ms`;
  }

  function getFamilyParts(family: string) {
    return familyPartsById[family] ?? family.split("_").filter(Boolean);
  }

  function isFamilyAllowed(family: string) {
    if (selectedModelFamilyIds.length === 0) return false;
    if (selectedModelFamilyIds.length === modelFamilyOptions.length) return true;

    const parts = getFamilyParts(family);
    if (componentMatchMode === "exact") {
      return (
        parts.length === selectedModelFamilyIds.length &&
        parts.every((part) => selectedModelFamilySet.has(part))
      );
    }

    return parts.some((part) => selectedModelFamilySet.has(part));
  }

  function familyText(family: string) {
    return getFamilyParts(family).map(formatFamily).join(" ");
  }

  function modelDisplayName(_id: string, fallback: string) {
    return fallback;
  }

  function modelMarker(id: string) {
    return getEntityMarker(id, catalog.models.findIndex((model) => model.id === id), "model");
  }

  function datasetMarker(id: string) {
    return getEntityMarker(id, catalog.datasets.findIndex((dataset) => dataset.id === id), "dataset");
  }

  function formatFamily(family: string) {
    const labels: Record<string, string> = {
      attn: "Attention",
      cnn: "Convolutional",
      dense: "Dense",
      fe: "Handcrafted",
      graph: "Graph",
      rnn: "Recurrent",
      spec: "Spectral",
    };
    const parts = getFamilyParts(family);

    if (labels[family]) return labels[family];
    if (parts.length > 1) return parts.map(formatFamily).join(" ");
    return family.replaceAll("_", " ");
  }

  function describeFamily(family: string) {
    const definitions: Record<string, string> = {
      attn: "Uses learned, input-dependent weights to emphasize relevant timesteps, sensor channels, or features; includes transformer-style attention.",
      cnn: "Uses learned convolutional filters over time or sensor channels to detect local activity patterns.",
      dense: "Uses fully connected layers in which each output combines all inputs, commonly for feature mixing or classification.",
      fe: "Uses manually designed statistical, temporal, or frequency features before classification instead of learning every representation end to end.",
      graph: "Represents sensors, channels, or body parts as connected nodes and learns from their relationships.",
      neural: "Uses trainable neural-network layers to learn representations directly from sensor data.",
      rnn: "Uses sequence layers such as LSTMs or GRUs that carry hidden state across timesteps to model temporal dependencies.",
      spec: "Transforms signals into frequency-domain representations or otherwise processes spectral features before classification.",
    };

    return definitions[family] ?? "Architecture building block used by this model.";
  }

  function getModelFamilyIds(models: Model[]) {
    return getModelFamilyOptions(models).map((item) => item.id);
  }

  function getModelFamilyOptions(models: Model[]): FilterOption[] {
    const ids = [...new Set(models.flatMap((model) => getFamilyParts(model.family)))];
    return ids
      .sort((a, b) => compareLabels(formatFamily(a), formatFamily(b)))
      .map((id) => ({ id, name: formatFamily(id), definition: describeFamily(id) }));
  }

  function scoreStyle(score: number | null) {
    if (score === null) return "";
    const normalized = Math.max(0, Math.min(1, score));
    const hue =
      normalized < 0.5
        ? interpolate(6, 42, normalized * 2)
        : interpolate(42, 145, (normalized - 0.5) * 2);
    const lightness =
      normalized < 0.5
        ? interpolate(91, 86, normalized * 2)
        : interpolate(86, 76, (normalized - 0.5) * 2);

    return `--score-bg: hsl(${hue} var(--heat-saturation) calc(${lightness}% - var(--heat-darken)));`;
  }

  function interpolate(start: number, end: number, amount: number) {
    return start + (end - start) * amount;
  }

  function getModelDetail(id: string) {
    return detailMap[id] ?? null;
  }

  function getDatasetDetail(id: string) {
    return datasetDetailMap[id] ?? null;
  }

  function modelInstitutions(id: string) {
    return getModelDetail(id)?.institutions ?? [];
  }

  function modelInstitutionSummary(id: string) {
    const institutions = modelInstitutions(id);
    const summary = institutions.length > 3
      ? [...institutions.slice(0, 2), "et al."]
      : institutions;
    const baselineDetail = classicalBaselineDetails[id];
    return baselineDetail ? [...summary, baselineDetail] : summary;
  }

  function openModelDetail(id: string) {
    selectedDetailDatasetId = null;
    selectedDetailModelId = id;
  }

  function closeModelDetail() {
    selectedDetailModelId = null;
  }

  function openDatasetDetail(id: string) {
    selectedDetailModelId = null;
    selectedDetailDatasetId = id;
  }

  function closeDatasetDetail() {
    selectedDetailDatasetId = null;
  }

  function closeDetailModal() {
    closeModelDetail();
    closeDatasetDetail();
  }

  function closeSiblingFilterDropdowns(event: Event) {
    const current = event.currentTarget as HTMLDetailsElement | null;
    if (!current?.open) return;

    current
      .closest(".filter-panel")
      ?.querySelectorAll<HTMLDetailsElement>(".dataset-filter details")
      .forEach((details) => {
        if (details !== current) details.open = false;
      });
  }

  function handleModelRowKeydown(event: KeyboardEvent, id: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openModelDetail(id);
    }
  }

  function handleDatasetKeydown(event: KeyboardEvent, id: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDatasetDetail(id);
    }
  }

  function handleDialogKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      closeDetailModal();
    }
  }

  function formatDetailMetric(value: string | null | undefined) {
    return value ?? "—";
  }

  function formatDatasetMetric(value: number | string | null | undefined) {
    if (typeof value === "number") return numberFormatter.format(value);
    return value ?? "—";
  }

  function getPaperLink(kind: "datasets" | "models", id: string) {
    return linkMap[kind][id] ?? null;
  }

  function hasPaperLink(kind: "datasets" | "models", id: string) {
    return Boolean(getPaperLink(kind, id)?.url);
  }

  function paperUrl(kind: "datasets" | "models", id: string) {
    return getPaperLink(kind, id)?.url ?? "";
  }

  function paperTitle(kind: "datasets" | "models", id: string, fallback: string) {
    return `Open paper: ${getPaperLink(kind, id)?.title ?? fallback}`;
  }

  function paperDisplayTitle(kind: "datasets" | "models", id: string, fallback: string) {
    return getPaperLink(kind, id)?.title ?? fallback;
  }

  function datasetInputId(id: string) {
    return `dataset-filter-${id}`;
  }

  function modelFamilyInputId(id: string) {
    return `model-family-filter-${id}`;
  }

  function modelInputId(id: string) {
    return `model-filter-${id}`;
  }

  function createScatterPlot(config: ScatterConfig, scale: ScatterScale): ScatterPlot {
    const rawPoints = rows.flatMap((row) => {
      const metricValue = scatterMetricValue(row, config.metric);
      const macroF1 = selectedMeanMacroF1(row.id);

      if (
        typeof metricValue !== "number" ||
        !Number.isFinite(metricValue) ||
        (scale === "log" && metricValue <= 0) ||
        macroF1 === null
      ) {
        return [];
      }

      return [
        {
          model_id: row.id,
          name: row.name,
          family: row.family,
          color: modelMarker(row.id).color,
          x: metricValue,
          y: macroF1,
        },
      ];
    });
    const points: ScatterPoint[] = rawPoints.map((point) => {
      const dominators = rawPoints
        .filter((candidate) => candidate.model_id !== point.model_id && dominates(candidate, point))
        .map((candidate) => candidate.name);

      return {
        ...point,
        isPareto: dominators.length === 0,
        dominators,
      };
    });
    const frontierPoints = points
      .filter((point) => point.isPareto)
      .sort((a, b) => a.x - b.x || a.y - b.y || a.name.localeCompare(b.name));
    const allMacroF1 = points.map((point) => point.y);

    if (points.length === 0 || allMacroF1.length === 0) {
      return {
        ...config,
        scale,
        points,
        frontierPoints,
        xMin: scale === "log" ? 0.1 : 0,
        xMax: 1,
        yMin: 0.45,
        yMax: 0.7,
        xTicks: scale === "log" ? [0.1, 1] : createLinearTicks(0, 1, 4),
        yTicks: createLinearTicks(0.45, 0.7, 4),
        missingCount: rows.length,
      };
    }

    const xValues = points.map((point) => point.x);
    let xMin = 0;
    let xMax = niceCostMax(Math.max(...xValues, 1));
    let xTicks = createLinearTicks(xMin, xMax, 4);

    if (scale === "log") {
      xMin = 10 ** Math.floor(Math.log10(Math.min(...xValues)));
      xMax = 10 ** Math.ceil(Math.log10(Math.max(...xValues)));

      if (xMin === xMax) {
        xMin /= 10;
        xMax *= 10;
      }

      xTicks = createLogTicks(xMin, xMax, 7);
    }

    const yMin = Math.max(0, Math.floor((Math.min(...allMacroF1) - 0.015) * 100) / 100);
    const yMax = Math.min(1, Math.ceil((Math.max(...allMacroF1) + 0.015) * 100) / 100);

    return {
      ...config,
      scale,
      points,
      frontierPoints,
      xMin,
      xMax,
      yMin,
      yMax,
      xTicks,
      yTicks: createLinearTicks(yMin, yMax, 4),
      missingCount: rows.length - points.length,
    };
  }

  /** Name the models on the front, at the first spot that hits no other label or marker. */
  function placeScatterLabels(chart: ScatterPlot) {
    const charWidth = 7.2;
    const height = 15;
    const markers = chart.points.map((point) => ({ x: plotX(point.x, chart), y: plotY(point.y, chart) }));
    const placed: Array<{ left: number; right: number; top: number; bottom: number }> = [];
    return chart.frontierPoints.map((point) => {
      const x = plotX(point.x, chart);
      const y = plotY(point.y, chart);
      const width = point.name.length * charWidth;
      const candidates = [
        { dx: 0, dy: -14 },
        { dx: 0, dy: 24 },
        { dx: -width / 2 - 12, dy: 5 },
        { dx: width / 2 + 12, dy: 5 },
        { dx: 0, dy: -30 },
        { dx: 0, dy: 40 },
        { dx: -width / 2 - 12, dy: -14 },
        { dx: width / 2 + 12, dy: 24 },
        { dx: 0, dy: -46 },
        { dx: 0, dy: 56 },
      ];
      const fit = (candidate: { dx: number; dy: number }) => {
        const minCenter = plotBox.left + width / 2 + 2;
        const maxCenter = plotBox.width - plotBox.right - width / 2;
        const center = Math.max(minCenter, Math.min(maxCenter, x + candidate.dx));
        const baseline = y + candidate.dy;
        return {
          center,
          baseline,
          box: {
            left: center - width / 2,
            right: center + width / 2,
            top: baseline - height + 3,
            bottom: baseline + 3,
          },
        };
      };
      const isFree = (option: ReturnType<typeof fit>) =>
        option.box.top >= plotBox.top - 12 &&
        option.box.bottom <= plotBox.height - plotBox.bottom &&
        !placed.some(
          (other) =>
            option.box.left < other.right &&
            option.box.right > other.left &&
            option.box.top < other.bottom &&
            option.box.bottom > other.top,
        ) &&
        !markers.some(
          (marker) =>
            marker.x > option.box.left - 8 &&
            marker.x < option.box.right + 8 &&
            marker.y > option.box.top - 8 &&
            marker.y < option.box.bottom + 8,
        );
      const options = candidates.map(fit);
      const chosen = options.find(isFree) ?? options[0];
      placed.push(chosen.box);
      return { id: point.model_id, name: point.name, x: chosen.center, y: chosen.baseline };
    });
  }

  function scatterMetricValue(row: LeaderboardRow, metric: ScatterMetric) {
    return isMcuMetric(metric) ? mcuRelativeCost(row.id, metric) : deviceMean(row.id, metric);
  }

  function dominates(
    candidate: { x: number; y: number },
    point: { x: number; y: number },
  ) {
    return (
      candidate.x <= point.x &&
      candidate.y >= point.y &&
      (candidate.x < point.x || candidate.y > point.y)
    );
  }

  function frontierPath(chart: ScatterPlot) {
    return chart.frontierPoints
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"} ${plotX(point.x, chart)} ${plotY(point.y, chart)}`,
      )
      .join(" ");
  }

  function createLinearTicks(min: number, max: number, steps: number) {
    if (steps <= 0 || max === min) return [min];
    return Array.from({ length: steps + 1 }, (_, index) => min + ((max - min) * index) / steps);
  }

  function createLogTicks(min: number, max: number, maxTicks: number) {
    const ticks: number[] = [];
    const minExponent = Math.floor(Math.log10(min));
    const maxExponent = Math.ceil(Math.log10(max));

    for (let exponent = minExponent; exponent <= maxExponent; exponent += 1) {
      for (const multiplier of [1, 2, 5]) {
        const tick = multiplier * 10 ** exponent;
        if (tick >= min && tick <= max) ticks.push(tick);
      }
    }

    if (ticks.length <= maxTicks) return ticks;

    const sampled = Array.from({ length: maxTicks }, (_, index) => {
      const tickIndex = Math.round((index * (ticks.length - 1)) / (maxTicks - 1));
      return ticks[tickIndex];
    });
    return [...new Set(sampled)];
  }

  function niceCostMax(value: number) {
    if (value <= 2) return Math.ceil(value * 10) / 10;
    if (value <= 10) return Math.ceil(value / 2) * 2;
    if (value <= 30) return Math.ceil(value / 5) * 5;
    return Math.ceil(value / 10) * 10;
  }

  function plotX(value: number, chart: ScatterPlot) {
    const innerWidth = plotBox.width - plotBox.left - plotBox.right;
    const position = chart.scale === "log"
      ? normalize(Math.log10(value), Math.log10(chart.xMin), Math.log10(chart.xMax), 0.5)
      : normalize(value, chart.xMin, chart.xMax, 0.5);
    return plotBox.left + position * innerWidth;
  }

  function plotY(value: number, chart: ScatterPlot) {
    const innerHeight = plotBox.height - plotBox.top - plotBox.bottom;
    return (
      plotBox.top +
      (1 - normalize(value, chart.yMin, chart.yMax, 0.5)) * innerHeight
    );
  }

  function formatScatterTick(value: number, metric: ScatterMetric) {
    if (value >= 1000) return `${(value / 1000).toFixed(value >= 10_000 ? 0 : 1)}k`;
    if (value >= 10) return value.toFixed(0);
    if (value >= 1) return value.toFixed(1);
    if (value >= 0.1) return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
    return value.toPrecision(1);
  }

  function formatScatterF1Tick(value: number) {
    return `${(value * 100).toFixed(0)}%`;
  }

  function formatScatterValue(value: number, _metric: ScatterMetric) {
    return `${value.toFixed(2)} ${activeScatterConfig.unit}`;
  }

  function showScatterTooltip(event: MouseEvent, point: ScatterPoint) {
    scatterTooltip = {
      point,
      x: event.clientX,
      y: event.clientY,
    };
  }

  function moveScatterTooltip(event: MouseEvent) {
    if (!scatterTooltip) return;
    scatterTooltip = {
      ...scatterTooltip,
      x: event.clientX,
      y: event.clientY,
    };
  }

  function showFocusedScatterTooltip(event: FocusEvent, point: ScatterPoint) {
    const bounds = (event.currentTarget as SVGGraphicsElement).getBoundingClientRect();
    scatterTooltip = {
      point,
      x: bounds.left + bounds.width / 2,
      y: bounds.top,
    };
  }

  function hideScatterTooltip() {
    scatterTooltip = null;
  }

  function tooltipX(x: number) {
    return Math.min(Math.max(x, 150), Math.max(150, window.innerWidth - 150));
  }

  function showComponentTooltip(event: MouseEvent | FocusEvent, text: string) {
    const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect();
    componentTooltip = {
      text,
      x: tooltipX(event instanceof MouseEvent ? event.clientX : bounds.left + bounds.width / 2),
      y: event instanceof MouseEvent ? event.clientY : bounds.top,
    };
  }

  function moveComponentTooltip(event: MouseEvent) {
    if (!componentTooltip) return;
    componentTooltip = {
      ...componentTooltip,
      x: tooltipX(event.clientX),
      y: event.clientY,
    };
  }

  function hideComponentTooltip() {
    componentTooltip = null;
  }

  function handleComponentTooltipClick(event: MouseEvent, text: string) {
    event.preventDefault();
    event.stopPropagation();
    showComponentTooltip(event, text);
  }

  function handleComponentTooltipKeydown(event: KeyboardEvent, text: string) {
    event.stopPropagation();
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      showComponentTooltip(event as unknown as FocusEvent, text);
    } else if (event.key === "Escape") {
      hideComponentTooltip();
    }
  }
</script>

<svelte:window onkeydown={handleDialogKeydown} />

<div class="bench-stack">
  <section class="arena-panel filter-panel">
    <div class="panel-header">
      <h2>Filters</h2>
      <button type="button" class="filter-reset-all" onclick={resetAllFilters}>Reset all</button>
    </div>

    <div class="filter-content">
      <div class="dataset-filter">
        <span class="filter-label">Datasets</span>
        <details ontoggle={closeSiblingFilterDropdowns}>
          <summary aria-label="Datasets">
            <span>{selectedDatasetSummary}</span>
            <span class="filter-count">
              {selectedDatasetIds.length}/{catalog.datasets.length}
            </span>
          </summary>
          <div class="dataset-menu">
            <div class="dataset-actions" aria-label="Dataset selection actions">
              <button type="button" data-filter-action="all-datasets" onclick={selectAllDatasets}>
                All
              </button>
              <button type="button" data-filter-action="none-datasets" onclick={clearDatasets}>
                None
              </button>
              <button type="button" data-filter-action="top-datasets" onclick={selectTopDatasets}>
                Top 10
              </button>
            </div>
            <div class="dataset-options">
              {#each datasetFilterOptions as item}
                <div class="dataset-option" data-dataset-id={item.id}>
                  <input
                    id={datasetInputId(item.id)}
                    type="checkbox"
                    value={item.id}
                    checked={isDatasetSelected(item.id)}
                    onchange={() => toggleDataset(item.id)}
                  />
                  <label
                    class="dataset-check"
                    for={datasetInputId(item.id)}
                    aria-label={`Toggle ${item.name}`}
                  ></label>
                  <button
                    type="button"
                    class="dataset-option-link dataset-option-detail"
                    title={`Open dataset overview: ${item.name}`}
                    onclick={() => openDatasetDetail(item.id)}
                  >
                    {item.name}
                  </button>
                </div>
              {/each}
            </div>
          </div>
        </details>
      </div>

      <div class="dataset-filter">
        <span class="filter-label">Models</span>
        <details ontoggle={closeSiblingFilterDropdowns}>
          <summary aria-label="Models">
            <span>{selectedModelSummary}</span>
            <span class="filter-count">
              {selectedModelIds.length}/{catalog.models.length}
            </span>
          </summary>
          <div class="dataset-menu">
            <div class="dataset-actions" aria-label="Model selection actions">
              <button type="button" data-filter-action="all-models" onclick={selectAllModels}>
                All
              </button>
              <button type="button" data-filter-action="none-models" onclick={clearModels}>
                None
              </button>
              <button type="button" data-filter-action="top-models" onclick={selectTopModels}>
                Top 10
              </button>
            </div>
            <div class="dataset-options">
              {#each modelFilterOptions as item}
                <div class="dataset-option" data-model-id={item.id}>
                  <input
                    id={modelInputId(item.id)}
                    type="checkbox"
                    value={item.id}
                    checked={isModelSelected(item.id)}
                    onchange={() => toggleModel(item.id)}
                  />
                  <label
                    class="dataset-check"
                    for={modelInputId(item.id)}
                    aria-label={`Toggle ${item.name}`}
                  ></label>
                  <button
                    type="button"
                    class="dataset-option-link dataset-option-detail"
                    title={`Open model overview: ${item.name}`}
                    onclick={() => openModelDetail(item.id)}
                  >
                    {item.name}
                  </button>
                </div>
              {/each}
            </div>
          </div>
        </details>
      </div>

      <div class="dataset-filter">
        <span class="filter-label">Building Blocks</span>
        <details ontoggle={closeSiblingFilterDropdowns}>
          <summary aria-label="Building blocks">
            <span>{selectedModelFamilySummary}</span>
            <span class="filter-count">
              {selectedModelFamilyIds.length}/{modelFamilyOptions.length}
            </span>
          </summary>
          <div class="dataset-menu">
            <div class="dataset-actions component-actions" aria-label="Building block selection actions">
              <button type="button" onclick={selectAllModelFamilies}>All</button>
              <button type="button" onclick={clearModelFamilies}>None</button>
              <label class="component-match-toggle">
                <input
                  type="checkbox"
                  checked={componentMatchMode === "exact"}
                  onchange={(event) =>
                    (componentMatchMode = event.currentTarget.checked ? "exact" : "inclusive")}
                />
                <span>Exact combination</span>
              </label>
            </div>
            <div class="dataset-options">
              {#each modelFamilyOptions as item}
                <div class="dataset-option" data-model-family-id={item.id}>
                  <input
                    id={modelFamilyInputId(item.id)}
                    type="checkbox"
                    value={item.id}
                    checked={isModelFamilySelected(item.id)}
                    onchange={() => toggleModelFamily(item.id)}
                  />
                  <label
                    class="dataset-check"
                    for={modelFamilyInputId(item.id)}
                    aria-label={`Toggle ${item.name}`}
                  ></label>
                  <label class="dataset-name-toggle" for={modelFamilyInputId(item.id)}>
                    <span class="family-pill">
                      {item.name}
                      <span
                        class="family-pill-info"
                        tabindex="0"
                        aria-label={`Definition: ${item.definition ?? ""}`}
                        onmouseenter={(event) => showComponentTooltip(event, item.definition ?? "")}
                        onmousemove={moveComponentTooltip}
                        onmouseleave={hideComponentTooltip}
                        onfocus={(event) => showComponentTooltip(event, item.definition ?? "")}
                        onblur={hideComponentTooltip}
                        onclick={(event) => handleComponentTooltipClick(event, item.definition ?? "")}
                        onkeydown={(event) => handleComponentTooltipKeydown(event, item.definition ?? "")}
                      >
                        ⓘ
                      </span>
                    </span>
                  </label>
                </div>
              {/each}
            </div>
          </div>
        </details>
      </div>

      <label class="dataset-filter window-size-filter">
        <span class="filter-label">Window Length</span>
        <span class="window-size-select">
          <select bind:value={selectedWindowSizeSeconds} aria-label="Window length">
            {#each windowSizeOptions as seconds}
              <option value={seconds}>{formatWindowSize(seconds)}</option>
            {/each}
          </select>
        </span>
      </label>

      <label
        class="dataset-filter window-size-filter"
        class:filter-inactive={!deviceFilterApplies}
        title={deviceFilterApplies ? undefined : activeView === "deployment" ? "The Deployment tab always shows all devices" : "This view does not depend on the device"}
      >
        <span class="filter-label">Device</span>
        <span class="window-size-select">
          <select bind:value={selectedDevice} onchange={setDeviceSort} disabled={!deviceFilterApplies} aria-label="Device for the Pareto fronts and trade-offs">
            <option value="phone">Phone</option>
            <option value="watch">Watch</option>
            <option value="mcu">MCU</option>
          </select>
        </span>
      </label>
    </div>
  </section>

  <div class="benchmark-view-shell">
  <div class="view-switcher" aria-label="Benchmark views" role="tablist">
    <button
      id="leaderboard-tab"
      type="button"
      role="tab"
      aria-selected={activeView === "leaderboard"}
      aria-controls="leaderboard-view"
      class:active={activeView === "leaderboard"}
      onclick={() => (activeView = "leaderboard")}
    >
      Rankings
    </button>
    <button
      id="pareto-tab"
      type="button"
      role="tab"
      aria-selected={activeView === "pareto"}
      aria-controls="pareto-view"
      class:active={activeView === "pareto"}
      onclick={() => (activeView = "pareto")}
    >
      Trade-offs
    </button>
    <button
      id="best-tab"
      type="button"
      role="tab"
      aria-selected={activeView === "best"}
      aria-controls="best-view"
      class:active={activeView === "best"}
      onclick={() => (activeView = "best")}
    >
      Gap to Best
    </button>
    <button
      id="matrix-tab"
      type="button"
      role="tab"
      aria-selected={activeView === "matrix"}
      aria-controls="matrix-view"
      class:active={activeView === "matrix"}
      onclick={() => (activeView = "matrix")}
    >
      Score Matrix
    </button>
    <button
      id="deployment-tab"
      type="button"
      role="tab"
      aria-selected={activeView === "deployment"}
      aria-controls="deployment-view"
      class:active={activeView === "deployment"}
      onclick={() => (activeView = "deployment")}
    >
      Deployment
    </button>
    <button
      id="gap-tab"
      type="button"
      role="tab"
      aria-selected={activeView === "gap"}
      aria-controls="gap-view"
      class:active={activeView === "gap"}
      onclick={() => (activeView = "gap")}
    >
      Generalization Gap
    </button>
  </div>

  {#if activeView === "leaderboard"}
  <div
    id="leaderboard-view"
    class="arena-panel"
    role="tabpanel"
    aria-labelledby="leaderboard-tab"
  >
      <div class="panel-header">
        <div class="panel-heading">
        <h2>Rankings</h2>
          <p>Compare recognition performance across models, and how often each model lies on a per-dataset Pareto front on the selected device.</p>
        </div>
      </div>

    <div class="table-wrap leaderboard-wrap">
      <table class="leaderboard-table">
        <thead>
          <tr>
            <th>Model</th>
            <th aria-sort={sortAria("net_improvement")}>
              <span class="metric-heading">
                <button
                  type="button"
                  class:active-sort={sortKey === "net_improvement"}
                  class="sort-button"
                  onclick={() => setSort("net_improvement")}
                >
                  <span class="heading-label">
                    Net Mean Test Macro-F1 Improvement
                    <span
                      class="info-tip"
                      title={metricInfo.netImprovement}
                      aria-label={metricInfo.netImprovement}
                      data-tip={metricInfo.netImprovement}
                    >
                      ⓘ
                    </span>
                  </span>
                  <span class="sort-glyph" aria-hidden="true">
                    <span
                      class:active-arrow={sortKey === "net_improvement" && sortDirection === "asc"}
                    ></span>
                    <span
                      class:active-arrow={sortKey === "net_improvement" && sortDirection === "desc"}
                    ></span>
                  </span>
                </button>
              </span>
            </th>
            <th>Building Blocks</th>
            <th aria-sort={sortAria("macro_f1")}>
              <span class="metric-heading">
                <button
                  type="button"
                  class:active-sort={sortKey === "macro_f1"}
                  class="sort-button"
                  onclick={() => setSort("macro_f1")}
                >
                  <span class="heading-label">
                    MEAN TEST MACRO-F1
                    <span
                      class="info-tip"
                      title={metricInfo.macroF1}
                      aria-label={metricInfo.macroF1}
                      data-tip={metricInfo.macroF1}
                    >
                      ⓘ
                    </span>
                  </span>
                  <span class="sort-glyph" aria-hidden="true">
                    <span class:active-arrow={sortKey === "macro_f1" && sortDirection === "asc"}></span>
                    <span class:active-arrow={sortKey === "macro_f1" && sortDirection === "desc"}></span>
                  </span>
                </button>
              </span>
            </th>
            {#each activeCosts as cost}
              {@const key = `pareto:${cost.metric}` as SortKey}
              <th aria-sort={sortAria(key)}>
                <span class="metric-heading">
                  <button
                    type="button"
                    class:active-sort={sortKey === key}
                    class="sort-button"
                    onclick={() => setSort(key)}
                  >
                    <span class="heading-label">
                      Share of Fronts: {cost.label}
                      <span
                        class="info-tip"
                        title={metricInfo.pareto}
                        aria-label={metricInfo.pareto}
                        data-tip={metricInfo.pareto}
                      >
                        ⓘ
                      </span>
                    </span>
                    <span class="sort-glyph" aria-hidden="true">
                      <span class:active-arrow={sortKey === key && sortDirection === "asc"}></span>
                      <span class:active-arrow={sortKey === key && sortDirection === "desc"}></span>
                    </span>
                  </button>
                </span>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as row}
            {@const marker = modelMarker(row.id)}
            <tr
              class="clickable-row"
              role="button"
              tabindex="0"
              aria-label={`Open model details: ${row.name}`}
              onclick={() => openModelDetail(row.id)}
              onkeydown={(event) => handleModelRowKeydown(event, row.id)}
            >
              <td class="model-cell">
                <span class="model-name-line">
                  <svg class="entity-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                    <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                  </svg>
                  <span class="model-title-button">{row.name}</span>
                </span>
                <span class="phone-tags" aria-hidden="true">
                  {getFamilyParts(row.family).map((part) => familyShortLabels[part] ?? formatFamily(part)).join(" · ")}
                </span>
                <span class="institution-list">
                  {#each modelInstitutionSummary(row.id) as institution, index}
                    <span>{institution}{index < modelInstitutionSummary(row.id).length - 1 ? " · " : ""}</span>
                  {:else}
                    <span>Affiliations withheld during review</span>
                  {/each}
                </span>
              </td>
              <td class="net-cell" class:negative-score={netDirection(row.netImprovement) === "down"}>
                {#if row.netImprovement === null}
                  <span class="pending">pending</span>
                {:else}
                  <div class="net-visual" style={netBarStyle(row)}>
                    <div class="net-score">
                      <strong class:best-score={isBestScore(row, "netImprovement")}>
                        <span
                          class="net-direction"
                          class:down={netDirection(row.netImprovement) === "down"}
                          class:flat={netDirection(row.netImprovement) === "flat"}
                          aria-hidden="true"
                        ></span>
                        {formatNetImprovement(row.netImprovement)}
                      </strong>
                      <span>{formatNetImprovementCi(row.netImprovementCi95)}</span>
                    </div>
                    <div class="net-bar" aria-hidden="true">
                      <span class="net-fill"></span>
                      <span class="net-zero"></span>
                      <span class="net-ci-line"></span>
                      <span class="net-ci-cap net-ci-low"></span>
                      <span class="net-ci-cap net-ci-high"></span>
                    </div>
                  </div>
                {/if}
              </td>
              <td class="family">
                <div class="family-pill-list family-tag-list" aria-label={`Building blocks: ${familyText(row.family)}`}>
                  {#each getFamilyParts(row.family) as familyPart}
                    {@const tip = `${formatFamily(familyPart)}: ${describeFamily(familyPart)}`}
                    <span
                      class="family-pill family-tag"
                      role="note"
                      tabindex="0"
                      aria-label={tip}
                      onmouseenter={(event) => showComponentTooltip(event, tip)}
                      onmousemove={moveComponentTooltip}
                      onmouseleave={hideComponentTooltip}
                      onfocus={(event) => showComponentTooltip(event, tip)}
                      onblur={hideComponentTooltip}
                      onclick={(event) => handleComponentTooltipClick(event, tip)}
                      onkeydown={(event) => handleComponentTooltipKeydown(event, tip)}
                    >
                      {familyShortLabels[familyPart] ?? formatFamily(familyPart)}
                    </span>
                  {/each}
                </div>
              </td>
              <td class="number">
                <strong class:best-score={isBestScore(row, "macroF1")}>
                  {formatPercent(row.macroF1)}
                </strong>
              </td>
              {#each activeCosts as cost}
                {@const share = paretoShare(row.id, cost.metric)}
                {@const config = deploymentMetricConfigs.find((item) => item.metric === cost.metric)}
                <td class="number efficiency-cell">
                  <strong class:best-score={share !== null && share > 0 && share === bestParetoShares.get(cost.metric)}>
                    {formatPercent(share)}
                  </strong>
                  {#if !isMcuMetric(cost.metric)}
                    <span>{formatCost(deviceMean(row.id, cost.metric))} {config?.unit}</span>
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
  {/if}

  {#if activeView === "matrix"}
  <div
    id="matrix-view"
    class="arena-panel matrix-panel"
    role="tabpanel"
    aria-labelledby="matrix-tab"
  >
    <div class="panel-header">
      <div class="panel-heading">
        <h2>Dataset × Model Matrix</h2>
        <p>Inspect Test Macro-F1 or any deployment cost per dataset and model.</p>
      </div>
      <label class="pareto-field pareto-metric-field">
        <span class="pareto-field-label">Metric</span>
        <span class="pareto-select">
          <select
            value={matrixSelectValue}
            onchange={(event) => (matrixSelection = event.currentTarget.value as "macro_f1" | CostKey)}
            aria-label="Matrix metric"
          >
            <option value="macro_f1">Test Macro-F1 (%)</option>
            {#each activeCosts as cost}
              <option value={cost.key}>
                {deviceLabel} {cost.label} ({deploymentMetricConfigs.find((config) => config.metric === cost.metric)?.unit})
              </option>
            {/each}
          </select>
        </span>
      </label>
    </div>

    {#if matrixRows.length > 0 && visibleModels.length > 0}
    <div class="table-wrap matrix-wrap">
      <table class="matrix-table">
        <thead>
          <tr>
            <th class="sticky-col matrix-corner" aria-label="Datasets by models">
              <span class="matrix-corner-label matrix-corner-models">Models</span>
              <span class="matrix-corner-label matrix-corner-datasets">Datasets</span>
            </th>
            {#each visibleModels as model}
              {@const marker = modelMarker(model.id)}
              <th
                class="matrix-model-heading"
                title={`Open model details: ${model.name}`}
                onclick={() => openModelDetail(model.id)}
              >
                <span>
                  <button
                    class="matrix-model-button"
                    type="button"
                    onclick={() => openModelDetail(model.id)}
                  >
                    <svg class="entity-marker matrix-model-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                      <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                    </svg>
                    {model.name}
                  </button>
                </span>
              </th>
            {/each}
            {#if showMatrixMeans}
              <th
                class="matrix-mean-heading"
                title="Arithmetic mean of the displayed values across visible models for each dataset"
              >
                <span>Mean across models</span>
              </th>
            {/if}
          </tr>
        </thead>
        <tbody>
          {#each matrixRows as row}
            {@const marker = datasetMarker(row.id)}
            <tr>
              <th class="sticky-col dataset-cell" title={`${row.name} · ${row.id}`}>
                <button
                  class="dataset-title-button matrix-dataset-title-button"
                  type="button"
                  title={`Open dataset details: ${row.name}`}
                  onclick={() => openDatasetDetail(row.id)}
                >
                  <svg class="entity-marker matrix-dataset-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                    <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                  </svg>
                  {row.name}
                </button>
              </th>
              {#each row.cells as cell}
                <td
                  class:pending-cell={cell.value === null && !cell.flag}
                  style={matrixMetric === "macro_f1" ? scoreStyle(cell.value) : deploymentCellStyle(cell.value, row.min, row.max)}
                  title={`${row.name} × ${cell.modelName}: ${cell.value === null ? cell.reason : matrixValueLabel(cell.value)}`}
                >
                  {#if cell.flag}
                    <span class="deployment-flag">{cell.flag}</span>
                  {:else}
                    <strong>{formatMatrixValue(cell.value)}</strong>
                  {/if}
                </td>
              {/each}
              {#if showMatrixMeans}
                <td
                  class="matrix-mean-cell"
                  class:pending-cell={row.mean === null}
                  style={matrixMetric === "macro_f1" ? scoreStyle(row.mean) : ""}
                  title={`${row.name}: arithmetic mean across visible models · ${matrixValueLabel(row.mean)}`}
                >
                  <strong>{formatMatrixValue(row.mean)}</strong>
                </td>
              {/if}
            </tr>
          {/each}
          {#if showMatrixMeans}
            <tr class="matrix-summary-row">
              <th class="sticky-col dataset-cell matrix-summary-label">
                Mean across datasets
              </th>
              {#each matrixColumnMeans as cell}
                <td
                  class:pending-cell={cell.value === null}
                  style={matrixMetric === "macro_f1" ? scoreStyle(cell.value) : ""}
                  title={`${cell.modelName}: arithmetic mean across ${matrixRows.length} selected datasets · ${matrixValueLabel(cell.value)}`}
                >
                  <strong>{formatMatrixValue(cell.value)}</strong>
                </td>
              {/each}
              <td
                class="matrix-mean-cell"
                class:pending-cell={matrixGrandMean === null}
                style={matrixMetric === "macro_f1" ? scoreStyle(matrixGrandMean) : ""}
                title={`Arithmetic mean across all visible models × ${matrixRows.length} selected datasets · ${matrixValueLabel(matrixGrandMean)}`}
              >
                <strong>{formatMatrixValue(matrixGrandMean)}</strong>
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
    {:else}
      <div class="empty-view">
        Select at least one dataset and model to populate the score matrix.
      </div>
    {/if}
    {#if matrixConfig && matrixRows.length > 0 && visibleModels.length > 0}
      <p class="view-note matrix-note">
        Color runs per dataset on a log scale, green for the cheapest model. F: exceeds the MCU's flash.
        R: exceeds its RAM. M: the device ran out of memory. E: export or execution failed. These are
        results rather than gaps.{showMatrixMeans ? "" : " MCU means are omitted because models fit different datasets; see the Deployment tab for comparable ratios."}
      </p>
    {/if}
  </div>
  {/if}

  {#if activeView === "deployment"}
  <div
    id="deployment-view"
    class="arena-panel"
    role="tabpanel"
    aria-labelledby="deployment-tab"
  >
    <div class="panel-header">
      <div class="panel-heading">
        <h2>Deployment Cost</h2>
        <p>
          Latency, memory, flash, and energy measured on a {deployment.source.devices.phone}, a
          {deployment.source.devices.watch}, and a {deployment.source.devices.mcu} for
          {formatWindowSize(selectedWindowSizeSeconds)} windows.
        </p>
      </div>
    </div>

    {#if deploymentSummaryRows.length > 0 && selectedDatasets.length > 0}
      <section class="deployment-section">
        <div class="table-wrap">
          <table class="deployment-summary">
            <thead>
              <tr>
                <th rowspan="2">Model</th>
                <th rowspan="2">Macro-F1</th>
                <th class="group-heading" colspan="2">Phone (mean)</th>
                <th class="group-heading" colspan="2">Watch (mean)</th>
                <th class="group-heading" colspan="5">MCU (relative to {referenceModelName})</th>
              </tr>
              <tr>
                <th>Lat. (ms)</th>
                <th>Mem. (MB)</th>
                <th>Lat. (ms)</th>
                <th>Mem. (MB)</th>
                <th>Fits</th>
                <th>Lat.</th>
                <th>RAM</th>
                <th>Flash</th>
                <th>Energy</th>
              </tr>
            </thead>
            <tbody>
              {#each deploymentSummaryRows as row}
                {@const marker = modelMarker(row.id)}
                <tr>
                  <td>
                    <button
                      class="dataset-title-button"
                      type="button"
                      onclick={() => openModelDetail(row.id)}
                    >
                      <svg class="entity-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                        <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                      </svg>
                      {row.name}
                    </button>
                  </td>
                  <td class="heat-cell" style={scoreStyle(row.macroF1)}>{formatPercent(row.macroF1)}</td>
                  {#each [["phoneLatency", row.phoneLatency], ["phoneMemory", row.phoneMemory], ["watchLatency", row.watchLatency], ["watchMemory", row.watchMemory]] as [key, value]}
                    <td class="heat-cell group-start-{key === "phoneLatency" || key === "watchLatency"}" style={deploymentCellStyle(value as number | null, deploymentExtents[key as string].min, deploymentExtents[key as string].max)}>
                      {#if value === deploymentSummaryBest[key as "phoneLatency"] && value !== null}
                        <strong>{formatCost(value as number)}</strong>
                      {:else}
                        {formatCost(value as number | null)}
                      {/if}
                    </td>
                  {/each}
                  <td class="heat-cell group-start-true" style={scoreStyle(row.fits / selectedDatasets.length)}>{row.fits}/{selectedDatasets.length}</td>
                  {#each [["mcuLatency", row.mcuLatency], ["mcuRam", row.mcuRam], ["mcuFlash", row.mcuFlash], ["mcuEnergy", row.mcuEnergy]] as [key, value]}
                    <td class="heat-cell" class:few-fits={row.fits < mcuMinFits} style={deploymentCellStyle(value as number | null, deploymentExtents[key as string].min, deploymentExtents[key as string].max)}>
                      {#if value === deploymentSummaryBest[key as "mcuLatency"] && value !== null && row.fits >= mcuMinFits}
                        <strong>{formatCost(value as number)}</strong>
                      {:else}
                        {value === null ? "×" : formatCost(value as number)}
                      {/if}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="view-note">
          Color runs per column on a log scale, green for the cheapest model. Bold marks the lowest cost per column, on the MCU among models that fit at least {mcuMinFits} datasets. Higher is greener for Macro-F1 and Fits. MCU ratios are geometric means over the datasets on
          which a model and {referenceModelName} both fit; below 1 is cheaper. Faded ratios rest on fewer
          than {mcuMinFits} datasets, and × means the model fits no selected dataset. Per-dataset values are
          in the Score Matrix tab.
        </p>
      </section>

    {:else}
      <div class="empty-view">Select at least one dataset and model to show deployment cost.</div>
    {/if}
  </div>
  {/if}

  {#if activeView === "best"}
  <div id="best-view" class="arena-panel" role="tabpanel" aria-labelledby="best-tab">
    <div class="panel-header">
      <div class="panel-heading">
        <h2>Gap to the Best Model</h2>
        <p>
          How many Test Macro-F1 points each model is behind the best model on each dataset, which removes
          differences in dataset difficulty (0 = best on that dataset).
        </p>
      </div>
    </div>

    {#if bestGapColumns.length > 0}
      <div class="table-wrap">
        <svg
          class="gap-chart"
          viewBox={`0 0 ${bestBox.width} ${bestBox.height}`}
          role="img"
          aria-label={`Gap to the best model per model for ${formatWindowSize(selectedWindowSizeSeconds)} windows. Highest Mean Test Macro-F1: ${bestGapColumns[0].name}, mean gap ${bestGapColumns[0].mean.toFixed(1)} points.`}
        >
          <g class="gap-grid" aria-hidden="true">
            {#each bestTicks as tick}
              <line x1={bestBox.left} x2={bestBox.width - bestBox.right} y1={bestY(tick)} y2={bestY(tick)}></line>
              <text x={bestBox.left - 8} y={bestY(tick)} text-anchor="end" dominant-baseline="middle">{tick}</text>
            {/each}
          </g>
          <text
            text-anchor="middle"
            transform={`translate(14 ${(bestBox.top + bestBox.height - bestBox.bottom) / 2}) rotate(-90)`}
          >Gap to best model (percentage points)</text>
          <g class="gap-summary-labels">
            <text x={bestBox.left - 8} y="14" text-anchor="end">Best on</text>
            <text x={bestBox.left - 8} y="32" text-anchor="end">Mean F1</text>
            <text x={bestBox.left - 8} y="50" text-anchor="end">Mean gap</text>
          </g>
          {#each bestGapColumns as column, index}
            {@const x = bestX(index)}
            <text class="gap-mean-label" x={x} y="14" text-anchor="middle">{column.wins}</text>
            <text class="gap-mean-label" x={x} y="32" text-anchor="middle">{((column.meanF1 ?? 0) * 100).toFixed(1)}</text>
            <text class="gap-mean-label" x={x} y="50" text-anchor="middle">{column.mean.toFixed(1)}</text>
            <rect
              class="gap-range"
              x={x - 16}
              width="32"
              y={bestY(column.mean + column.std)}
              height={Math.max(0, bestY(Math.max(0, column.mean - column.std)) - bestY(column.mean + column.std))}
            ></rect>
            {#each column.points as point}
              <circle
                class="gap-dot"
                cx={x + bestJitter(point.datasetId)}
                cy={bestY(point.gap)}
                r="3.2"
                fill={datasetMarker(point.datasetId).color}
                role="img"
                tabindex="0"
                aria-label={`${column.name} on ${point.name}: ${point.gap.toFixed(1)} points behind the best model`}
                onmouseenter={(event) => showComponentTooltip(event, `${column.name} on ${point.name}: ${point.gap.toFixed(1)} points behind the best (${formatPercent(point.score)} vs. ${formatPercent(point.best)})`)}
                onmousemove={moveComponentTooltip}
                onmouseleave={hideComponentTooltip}
                onfocus={(event) => showComponentTooltip(event, `${column.name} on ${point.name}: ${point.gap.toFixed(1)} points behind the best (${formatPercent(point.score)} vs. ${formatPercent(point.best)})`)}
                onblur={hideComponentTooltip}
              ></circle>
            {/each}
            <line class="gap-mean" x1={x - 18} x2={x + 18} y1={bestY(column.mean)} y2={bestY(column.mean)}></line>
            <text
              text-anchor="end"
              dominant-baseline="middle"
              transform={`translate(${x + 3} ${bestBox.height - bestBox.bottom + 8}) rotate(-50)`}
            >{column.name}</text>
          {/each}
        </svg>
      </div>
      <p class="view-note">
        Dots are datasets, the tick is the model's mean gap, and the band spans ±1 standard deviation.
        Models are sorted by Mean Test Macro-F1. The rows on top give the number of selected datasets on which
        a model is best, its Mean Test Macro-F1, and its mean gap. The best model on a dataset is taken over all
        models, even if some are hidden by the filters. (cl.) marks classical baselines.
      </p>
    {:else}
      <div class="empty-view">Select at least one dataset and model to show the gap to the best model.</div>
    {/if}
  </div>
  {/if}

  {#if activeView === "gap"}
  <div id="gap-view" class="arena-panel" role="tabpanel" aria-labelledby="gap-tab">
    <div class="panel-header">
      <div class="panel-heading">
        <h2>Generalization Gap to Unseen Subjects</h2>
        <p>
          Validation minus Test Macro-F1 per dataset. Validation windows come from the training
          subjects and test windows from held-out subjects, so a large gap points to a strong shift
          between users.
        </p>
      </div>
    </div>

    {#if gapColumns.length > 0}
      <div class="table-wrap">
        <svg
          class="gap-chart"
          viewBox={`0 0 ${gapBox.width} ${gapBox.height}`}
          role="img"
          aria-label={`Generalization gap per dataset for ${formatWindowSize(selectedWindowSizeSeconds)} windows. Largest mean gap: ${gapColumns[0].name}, ${gapColumns[0].mean.toFixed(1)} points.`}
        >
          <g class="gap-grid" aria-hidden="true">
            {#each gapTicks as tick}
              <line x1={gapBox.left} x2={gapBox.width - gapBox.right} y1={gapY(tick)} y2={gapY(tick)}></line>
              <text x={gapBox.left - 8} y={gapY(tick)} text-anchor="end" dominant-baseline="middle">{tick}</text>
            {/each}
          </g>
          <text
            text-anchor="middle"
            transform={`translate(14 ${(gapBox.top + gapBox.height - gapBox.bottom) / 2}) rotate(-90)`}
          >Generalization gap (percentage points)</text>
          {#each gapColumns as column, index}
            {@const x = gapX(index)}
            <rect
              class="gap-range"
              x={x - 12}
              width="24"
              y={gapY(column.mean + column.std)}
              height={Math.max(0, gapY(column.mean - column.std) - gapY(column.mean + column.std))}
            ></rect>
            {#each column.points as point}
              {@const marker = modelMarker(point.modelId)}
              <circle
                class="gap-dot"
                cx={x + gapJitter(point.modelId)}
                cy={gapY(point.gap)}
                r="3.4"
                fill={marker.color}
                role="img"
                tabindex="0"
                aria-label={`${column.name} × ${point.name}: gap ${point.gap.toFixed(1)} points`}
                onmouseenter={(event) => showComponentTooltip(event, `${column.name} × ${point.name}: gap ${point.gap.toFixed(1)} points (val ${formatPercent(point.val)}, test ${formatPercent(point.test)})`)}
                onmousemove={moveComponentTooltip}
                onmouseleave={hideComponentTooltip}
                onfocus={(event) => showComponentTooltip(event, `${column.name} × ${point.name}: gap ${point.gap.toFixed(1)} points (val ${formatPercent(point.val)}, test ${formatPercent(point.test)})`)}
                onblur={hideComponentTooltip}
              ></circle>
            {/each}
            <line class="gap-mean" x1={x - 14} x2={x + 14} y1={gapY(column.mean)} y2={gapY(column.mean)}></line>
            <text
              text-anchor="end"
              dominant-baseline="middle"
              transform={`translate(${x + 3} ${gapBox.height - gapBox.bottom + 8}) rotate(-50)`}
            >{column.name}</text>
            <text class="gap-mean-label" x={x} y={gapBox.top - 10} text-anchor="middle">{column.mean.toFixed(1)}</text>
          {/each}
        </svg>
      </div>
      <p class="view-note">
        Datasets are sorted by mean gap, given above each column. Dots are models, the tick is the mean
        over the visible models, and the band spans ±1 standard deviation. Validation scores also pick
        the early-stopping epoch, so they are slightly optimistic on every dataset.
      </p>
    {:else}
      <div class="empty-view">Select at least one dataset and model to show the generalization gap.</div>
    {/if}
  </div>
  {/if}

  {#if activeView === "pareto"}
    <div
      id="pareto-view"
      class="arena-panel scatter-panel"
      role="tabpanel"
      aria-labelledby="pareto-tab"
    >
      <div class="panel-header">
        <div class="panel-heading">
          <h2>Trade-offs Between Recognition Performance and Deployment Cost</h2>
          <p>Explore how recognition performance trades off against each deployment cost on the device selected in the filters.</p>
        </div>
        <div class="pareto-controls">
          <label class="pareto-field pareto-metric-field">
            <span class="pareto-field-label">X-axis</span>
            <span class="pareto-select">
              <select
                value={activeCost.key}
                onchange={(event) => (selectedCost = event.currentTarget.value as CostKey)}
                aria-label="Pareto cost metric"
              >
                {#each activeCosts as cost}
                  <option value={cost.key}>{deviceLabel} {cost.label}</option>
                {/each}
              </select>
            </span>
          </label>
          <label class="pareto-field pareto-scale-field">
            <span class="pareto-field-label">Scale</span>
            <span class="pareto-select">
              <select bind:value={scatterScale} aria-label="Pareto x-axis scale">
                <option value="log">Logarithmic</option>
                <option value="linear">Linear</option>
              </select>
            </span>
          </label>
          <label class="frontier-toggle">
            <input type="checkbox" bind:checked={showParetoFrontier} />
            <span>Show front</span>
          </label>
        </div>
      </div>

      {#if scatterPlot.points.length > 0}
        <div class="scatter-grid pareto-grid">
          <article class="scatter-plot pareto-plot">
            <h3>{deviceLabel}: Macro-F1 vs. {activeCost.label}</h3>
            <svg
              class="scatter-chart"
              viewBox={`0 0 ${plotBox.width} ${plotBox.height}`}
              role="img"
              aria-label={`${scatterPlot.title}. ${scatterPlot.frontierPoints.length} Pareto-optimal models.`}
            >
              <g class="scatter-grid-lines" aria-hidden="true">
                {#each scatterPlot.yTicks as tick}
                  <line
                    x1={plotBox.left}
                    x2={plotBox.width - plotBox.right}
                    y1={plotY(tick, scatterPlot)}
                    y2={plotY(tick, scatterPlot)}
                  ></line>
                {/each}
              </g>
              <g class="scatter-axis">
                <line
                  x1={plotBox.left}
                  x2={plotBox.left}
                  y1={plotBox.top}
                  y2={plotBox.height - plotBox.bottom}
                ></line>
                <line
                  x1={plotBox.left}
                  x2={plotBox.width - plotBox.right}
                  y1={plotBox.height - plotBox.bottom}
                  y2={plotBox.height - plotBox.bottom}
                ></line>
              </g>
              <g class="scatter-ticks">
                {#each scatterPlot.xTicks as tick}
                  <g>
                    <line
                      x1={plotX(tick, scatterPlot)}
                      x2={plotX(tick, scatterPlot)}
                      y1={plotBox.height - plotBox.bottom}
                      y2={plotBox.height - plotBox.bottom + 5}
                    ></line>
                    <text
                      x={plotX(tick, scatterPlot)}
                      y={plotBox.height - plotBox.bottom + 20}
                      text-anchor="middle"
                    >
                      {formatScatterTick(tick, scatterPlot.metric)}
                    </text>
                  </g>
                {/each}
                {#each scatterPlot.yTicks as tick}
                  <g>
                    <line
                      x1={plotBox.left - 5}
                      x2={plotBox.left}
                      y1={plotY(tick, scatterPlot)}
                      y2={plotY(tick, scatterPlot)}
                    ></line>
                    <text
                      x={plotBox.left - 9}
                      y={plotY(tick, scatterPlot)}
                      dominant-baseline="middle"
                      text-anchor="end"
                    >
                      {formatScatterF1Tick(tick)}
                    </text>
                  </g>
                {/each}
              </g>
              <text
                class="scatter-axis-title"
                x={(plotBox.left + plotBox.width - plotBox.right) / 2}
                y={plotBox.height - 8}
                text-anchor="middle"
              >
                {scatterPlot.xLabel}{scatterPlot.scale === "log" ? " (log scale)" : ""}
              </text>
              <text
                class="scatter-axis-title"
                dominant-baseline="middle"
                text-anchor="middle"
                transform={`translate(14 ${(plotBox.top + plotBox.height - plotBox.bottom) / 2}) rotate(-90)`}
              >
                Mean Test Macro-F1
              </text>
              {#if showParetoFrontier && scatterPlot.frontierPoints.length > 1}
                <path
                  class="pareto-frontier"
                  d={frontierPath(scatterPlot)}
                  aria-hidden="true"
                ></path>
              {/if}
              <g class="scatter-points">
                {#each scatterPlot.points as point}
                  {@const marker = modelMarker(point.model_id)}
                  <g
                    class="scatter-point"
                    class:pareto-point={point.isPareto}
                    class:dominated-point={!point.isPareto}
                    role="button"
                    tabindex="0"
                    aria-label={`${point.name}: ${formatPercent(point.y)}, ${formatScatterValue(point.x, scatterPlot.metric)}. ${point.isPareto ? "Pareto-optimal" : "Dominated"}. Open model details.`}
                    onclick={() => openModelDetail(point.model_id)}
                    onkeydown={(event) => handleModelRowKeydown(event, point.model_id)}
                    onfocus={(event) => showFocusedScatterTooltip(event, point)}
                    onblur={hideScatterTooltip}
                    onmouseenter={(event) => showScatterTooltip(event, point)}
                    onmousemove={moveScatterTooltip}
                    onmouseleave={hideScatterTooltip}
                  >
                    <title>{point.name}: {point.isPareto ? "Pareto-optimal" : "dominated"}</title>
                    <g
                      class="scatter-marker"
                      transform={`translate(${plotX(point.x, scatterPlot)} ${plotY(point.y, scatterPlot)})`}
                    >
                      <path class="scatter-marker-shape" d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                    </g>
                  </g>
                {/each}
              </g>
              {#if showParetoFrontier}
                <g class="scatter-labels" aria-hidden="true">
                  {#each scatterLabels as label}
                    <text x={label.x} y={label.y} text-anchor="middle">{label.name}</text>
                  {/each}
                </g>
              {/if}
            </svg>
            <ul class="scatter-legend" aria-label="Models in the plot">
              {#each scatterLegend as point}
                {@const marker = modelMarker(point.model_id)}
                <li class:on-front={point.isPareto}>
                  <button type="button" onclick={() => openModelDetail(point.model_id)}>
                    <svg class="entity-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                      <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                    </svg>
                    {point.name}
                  </button>
                </li>
              {/each}
            </ul>
            {#if isMcuMetric(activeScatterMetric)}
              <p class="view-note">
                Models fit different datasets, so absolute MCU costs are not comparable. Each cost is
                the geometric mean ratio to {referenceModelName} on the datasets where both fit
                (1 = same cost). Mean Test Macro-F1 uses all selected datasets, and models that fit no dataset
                are omitted{scatterPlot.missingCount > 0 ? ` (${scatterPlot.missingCount} here)` : ""}.
                See the Deployment tab for fit counts.
              </p>
            {/if}
          </article>
        </div>
        <section class="pareto-membership">
          <h3>{deviceLabel}: Pareto Fronts for {activeCost.label}</h3>
          <div class="table-wrap matrix-wrap">
            <table class="matrix-table">
              <thead>
                <tr>
                  <th class="sticky-col matrix-corner" aria-label="Datasets by models">
                    <span class="matrix-corner-label matrix-corner-models">Models</span>
                    <span class="matrix-corner-label matrix-corner-datasets">Datasets</span>
                  </th>
                  {#each paretoMatrixRows as model}
                    {@const marker = modelMarker(model.id)}
                    <th
                      class="matrix-model-heading"
                      title={`Open model details: ${model.name}`}
                      onclick={() => openModelDetail(model.id)}
                    >
                      <span>
                        <button
                          class="matrix-model-button"
                          type="button"
                          onclick={() => openModelDetail(model.id)}
                        >
                          <svg class="entity-marker matrix-model-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                            <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                          </svg>
                          {model.name}
                        </button>
                      </span>
                    </th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each paretoMatrixDatasets as dataset}
                  {@const marker = datasetMarker(dataset.id)}
                  <tr>
                    <th class="sticky-col dataset-cell" title={`${dataset.name} · ${dataset.id}`}>
                      <button
                        class="dataset-title-button matrix-dataset-title-button"
                        type="button"
                        title={`Open dataset details: ${dataset.name}`}
                        onclick={() => openDatasetDetail(dataset.id)}
                      >
                        <svg class="entity-marker matrix-dataset-marker" viewBox="-10 -10 20 20" aria-hidden="true">
                          <path d={getMarkerPath(marker.shape)} fill={marker.color} fill-rule="evenodd"></path>
                        </svg>
                        {dataset.name}
                      </button>
                    </th>
                    {#each paretoMatrixRows as model}
                      {@const on = isOnParetoFront(model.id, dataset.id, activeScatterMetric)}
                      <td
                        style={on ? scoreStyle(1) : ""}
                        title={`${dataset.name} × ${model.name}: ${on ? "on the Pareto front" : "not on the front"}`}
                      >
                        {#if on}<strong aria-label="On the front">✓</strong>{/if}
                      </td>
                    {/each}
                  </tr>
                {/each}
                <tr class="matrix-summary-row">
                  <th class="sticky-col dataset-cell matrix-summary-label">Share of fronts</th>
                  {#each paretoMatrixRows as model}
                    <td style={scoreStyle(model.share)} title={`${model.name}: on ${formatPercent(model.share)} of the selected datasets' fronts`}>
                      <strong>{formatCompactPercent(model.share)}</strong>
                    </td>
                  {/each}
                </tr>
              </tbody>
            </table>
          </div>
          <p class="view-note">
            A check means the model lies on that dataset's front of Test Macro-F1 against
            {activeCost.label}, computed on that dataset alone. Models are sorted by
            their share of fronts and datasets by Mean Test Macro-F1.{selectedDevice === "mcu" ? " Only models that fit on the MCU compete." : ""}
          </p>
        </section>
      {:else}
        <div class="empty-view">
          Select at least one model and dataset with deployment measurements to draw the Pareto front.
        </div>
      {/if}
    </div>
  {/if}
  </div>

  {#if scatterTooltip}
    <div
      class="scatter-tooltip"
      style={`left: ${scatterTooltip.x}px; top: ${scatterTooltip.y}px;`}
    >
      <strong>{scatterTooltip.point.name}</strong>
      <span>{formatPercent(scatterTooltip.point.y)} Macro-F1</span>
      <span>{formatScatterValue(scatterTooltip.point.x, scatterPlot.metric)}</span>
      <span class:pareto-status={scatterTooltip.point.isPareto}>
        {scatterTooltip.point.isPareto
          ? "Pareto-optimal"
          : `Dominated by ${scatterTooltip.point.dominators.slice(0, 2).join(", ")}`}
      </span>
    </div>
  {/if}

  {#if componentTooltip}
    <div
      class="component-tooltip"
      role="tooltip"
      style={`left: ${componentTooltip.x}px; top: ${componentTooltip.y}px;`}
    >
      {componentTooltip.text}
    </div>
  {/if}

  {#if selectedDetailModel && selectedDetail}
    <div class="modal-layer" role="presentation">
      <button
        class="modal-backdrop"
        type="button"
        aria-label="Close model details"
        onclick={closeModelDetail}
      ></button>
      <section
        class="model-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-detail-title"
      >
        <div class="model-modal-header">
          <div>
            <h2 id="model-detail-title">{selectedDetailModel.name}</h2>
            {#if hasPaperLink("models", selectedDetailModel.id)}
              <a
                class="modal-paper-title"
                href={paperUrl("models", selectedDetailModel.id)}
                title={paperTitle("models", selectedDetailModel.id, selectedDetailModel.name)}
                target="_blank"
                rel="noreferrer"
              >
                <span class="paper-title-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M7 3.5h7l3 3V20.5H7z" />
                    <path d="M14 3.5V7h3" />
                    <path d="M9.5 11h5M9.5 14h5M9.5 17h3" />
                  </svg>
                </span>
                <span>
                  {paperDisplayTitle("models", selectedDetailModel.id, selectedDetailModel.name)}
                </span>
              </a>
            {:else}
              <span class="modal-paper-title pending">
                <span class="paper-title-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M7 3.5h7l3 3V20.5H7z" />
                    <path d="M14 3.5V7h3" />
                    <path d="M9.5 11h5M9.5 14h5M9.5 17h3" />
                  </svg>
                </span>
                <span>
                  {paperDisplayTitle("models", selectedDetailModel.id, selectedDetailModel.name)}
                </span>
              </span>
            {/if}
            <ul class="author-list modal-author-list">
              {#if selectedDetail.authors.length > 0}
                {#each selectedDetail.authors as author}
                  <li>
                    <strong>{author.name}</strong>
                    <span>{author.affiliation}</span>
                  </li>
                {/each}
              {:else}
                <li><span>Author details withheld during review</span></li>
              {/if}
            </ul>
          </div>
          <button
            class="modal-close"
            type="button"
            aria-label="Close model details"
            onclick={closeModelDetail}
          ></button>
        </div>

        {#if selectedDetailRow}
          <div class="detail-metrics phone-results" aria-label="Results">
            <div>
              <span>Net Improvement</span>
              <strong>{formatNetImprovement(selectedDetailRow.netImprovement)}</strong>
            </div>
            {#each activeCosts as cost}
              <div>
                <span>Share of Fronts: {cost.label}</span>
                <strong>{formatPercent(paretoShare(selectedDetailRow.id, cost.metric))}</strong>
              </div>
            {/each}
          </div>
        {/if}

        <div class="detail-metrics" aria-label="Parameter and operation counts">
          <div>
            <span>Params*</span>
            <strong>{formatDetailMetric(selectedDetail.params)}</strong>
          </div>
          <div>
            <span>MACs*</span>
            <strong>{formatDetailMetric(selectedDetail.macs)}</strong>
          </div>
        </div>

        <p class="model-size-note">
          * <strong>Supplementary counts.</strong> Parameter and MAC counts are
          supplementary measures, given as means across the datasets for 3 s
          windows. Classical baselines have neither (-).
        </p>
      </section>
    </div>
  {/if}

  {#if selectedDetailDataset && selectedDatasetDetail}
    <div class="modal-layer" role="presentation">
      <button
        class="modal-backdrop"
        type="button"
        aria-label="Close dataset details"
        onclick={closeDatasetDetail}
      ></button>
      <section
        class="model-modal dataset-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-detail-title"
      >
        <div class="model-modal-header">
          <div>
            <h2 id="dataset-detail-title">{selectedDetailDataset.name}</h2>
            {#if hasPaperLink("datasets", selectedDetailDataset.id)}
              <a
                class="modal-paper-title"
                href={paperUrl("datasets", selectedDetailDataset.id)}
                title={paperTitle("datasets", selectedDetailDataset.id, selectedDetailDataset.name)}
                target="_blank"
                rel="noreferrer"
              >
                <span class="paper-title-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M7 3.5h7l3 3V20.5H7z" />
                    <path d="M14 3.5V7h3" />
                    <path d="M9.5 11h5M9.5 14h5M9.5 17h3" />
                  </svg>
                </span>
                <span>
                  {paperDisplayTitle("datasets", selectedDetailDataset.id, selectedDetailDataset.name)}
                </span>
              </a>
            {:else}
              <span class="modal-paper-title pending">
                <span class="paper-title-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M7 3.5h7l3 3V20.5H7z" />
                    <path d="M14 3.5V7h3" />
                    <path d="M9.5 11h5M9.5 14h5M9.5 17h3" />
                  </svg>
                </span>
                <span>
                  {paperDisplayTitle("datasets", selectedDetailDataset.id, selectedDetailDataset.name)}
                </span>
              </span>
            {/if}
            <ul class="author-list modal-author-list">
              {#if selectedDatasetPaperDetail?.authors?.length}
                {#each selectedDatasetPaperDetail.authors as author}
                  <li>
                    <strong>{author.name}</strong>
                    <span>{author.affiliation}</span>
                  </li>
                {/each}
              {:else}
                <li><span>Author details withheld during review</span></li>
              {/if}
            </ul>
          </div>
          <button
            class="modal-close"
            type="button"
            aria-label="Close dataset details"
            onclick={closeDatasetDetail}
          ></button>
        </div>

        <div class="detail-metrics dataset-detail-metrics" aria-label="Dataset statistics">
          <div>
            <span>Year</span>
            <strong>{selectedDatasetDetail.year}</strong>
          </div>
          <div>
            <span>Subjects</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.subjects)}</strong>
          </div>
          <div>
            <span>Activities</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.activities)}</strong>
          </div>
          <div>
            <span>Channels</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.channels)}</strong>
          </div>
          <div>
            <span>Settings</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.settings)}</strong>
          </div>
          <div>
            <span>Device Types</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.deviceTypes)}</strong>
          </div>
          <div>
            <span>Sensor Modalities</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.sensorModalities)}</strong>
          </div>
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .bench-stack {
    display: grid;
    gap: 14px;
    min-width: 0;
  }

  .arena-panel {
    min-width: 0;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel);
    overflow: hidden;
    box-shadow: none;
  }

  .filter-panel {
    position: relative;
    z-index: 20;
    overflow: visible;
  }

  .arena-panel.filter-panel {
    overflow: visible;
  }

  .benchmark-view-shell {
    min-width: 0;
    border: 1px solid var(--line-strong);
    border-radius: 14px 14px 8px 8px;
    background: var(--panel);
    overflow: hidden;
  }

  .benchmark-view-shell > .arena-panel {
    border: 0;
    border-radius: 0;
  }

  .benchmark-view-shell > .arena-panel > .panel-header {
    min-height: 92px;
    background: var(--panel);
  }

  .filter-panel > .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 7px 7px 0 0;
  }

  .filter-reset-all {
    flex: 0 0 auto;
    min-height: 30px;
    border: 1px solid var(--line-strong);
    border-radius: 7px;
    background: var(--panel);
    color: var(--muted-strong);
    padding: 0 10px;
    font: inherit;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
  }

  .filter-reset-all:hover,
  .filter-reset-all:focus-visible {
    border-color: var(--accent);
    color: var(--ink);
    outline: none;
  }

  .view-switcher {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0;
    min-width: 0;
    border: 0;
    border-bottom: 1px solid var(--line-strong);
    border-radius: 0;
    background: var(--panel-soft);
    padding: 4px 4px 0;
  }

  .view-switcher button {
    position: relative;
    z-index: 0;
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: var(--muted-strong);
    padding: 0 14px;
    font: inherit;
    font-size: 0.84rem;
    font-weight: 600;
    cursor: pointer;
    transition:
      border-color 120ms ease,
      background-color 120ms ease,
      color 120ms ease;
  }

  .view-switcher button:not(:first-child)::before {
    position: absolute;
    top: 10px;
    bottom: 10px;
    left: -1px;
    width: 1px;
    background: var(--line-strong);
    content: "";
    transition: opacity 120ms ease;
  }

  .view-switcher button.active::before,
  .view-switcher button.active + button::before {
    opacity: 0;
  }

  .view-switcher button:hover,
  .view-switcher button:focus-visible {
    background: var(--panel);
    color: var(--ink);
    outline: none;
  }

  .view-switcher button:focus-visible {
    border-color: var(--ink);
    box-shadow: 0 0 0 2px hsl(var(--ink-hsl) / 0.12);
  }

  .view-switcher button.active {
    z-index: 1;
    border-color: var(--line-strong);
    border-bottom-color: var(--panel);
    border-radius: 10px 10px 0 0;
    background: var(--panel);
    color: var(--ink);
    transform: translateY(1px);
    box-shadow:
      0 -1px 2px hsl(var(--ink-hsl) / 0.04),
      0 2px 7px hsl(var(--ink-hsl) / 0.05);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
    min-height: 65px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--line);
    background: var(--panel-soft);
  }

  .panel-heading {
    display: grid;
    min-width: 0;
    gap: 5px;
  }

  .panel-header p {
    margin: 0;
    color: var(--muted-strong);
    font-size: 0.8rem;
  }

  h2,
  p {
    margin: 0;
  }

  h2 {
    font-family: var(--display-serif);
    font-size: 1.3rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.05;
  }

  p,
  span {
    color: var(--muted);
  }

  th {
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .filter-content {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 14px;
    padding: 14px 16px 16px;
  }

  .filter-label {
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .dataset-filter {
    position: relative;
    display: grid;
    gap: 6px;
    min-width: 0;
    width: 100%;
  }

  .dataset-filter details {
    position: relative;
    width: 100%;
    min-width: 0;
  }

  .dataset-filter summary {
    display: flex;
    width: 100%;
    min-height: 36px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel-soft);
    color: var(--ink);
    padding: 0 10px;
    cursor: pointer;
    list-style: none;
  }

  .dataset-filter summary::-webkit-details-marker {
    display: none;
  }

  .dataset-filter summary::after {
    content: "";
    width: 7px;
    height: 7px;
    border-right: 1.5px solid var(--muted);
    border-bottom: 1.5px solid var(--muted);
    transform: rotate(45deg) translateY(-2px);
  }

  .dataset-filter details[open] summary::after {
    transform: rotate(225deg) translateY(-1px);
  }

  .dataset-filter summary span:first-child {
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-filter summary:focus-visible {
    outline: 2px solid hsl(var(--ink-hsl) / 0.28);
    outline-offset: 2px;
  }

  .dataset-filter summary:hover {
    border-color: var(--accent);
    background: var(--panel);
  }

  .window-size-select {
    position: relative;
    display: block;
  }

  .window-size-select::after {
    position: absolute;
    top: 50%;
    right: 12px;
    width: 7px;
    height: 7px;
    border-right: 1.5px solid var(--muted);
    border-bottom: 1.5px solid var(--muted);
    content: "";
    pointer-events: none;
    transform: translateY(-70%) rotate(45deg);
  }

  .window-size-select select {
    width: 100%;
    min-height: 36px;
    appearance: none;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel-soft);
    color: var(--ink);
    padding: 0 34px 0 10px;
    font: inherit;
    cursor: pointer;
  }

  .window-size-select select:hover {
    border-color: var(--accent);
    background: var(--panel);
  }

  .window-size-select select:focus-visible {
    outline: 2px solid hsl(var(--ink-hsl) / 0.28);
    outline-offset: 2px;
  }

  .filter-count {
    margin-left: auto;
    color: var(--muted);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.74rem;
  }

  .dataset-menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    right: 0;
    z-index: 10;
    width: auto;
    max-width: none;
    max-height: min(560px, 72vh);
    overflow: auto;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel);
    box-shadow: none;
  }

  .dataset-actions {
    position: sticky;
    top: 0;
    z-index: 1;
    display: flex;
    gap: 8px;
    padding: 8px;
    border-bottom: 1px solid var(--line);
    background: var(--panel-soft);
  }

  .dataset-actions button {
    min-height: 28px;
    border: 1px solid var(--line-strong);
    border-radius: 7px;
    background: var(--panel);
    color: var(--muted-strong);
    padding: 0 10px;
    cursor: pointer;
  }

  .dataset-actions button:hover {
    border-color: var(--accent);
    color: var(--ink);
  }

  .component-actions {
    flex-wrap: wrap;
    align-items: center;
  }

  .component-match-toggle {
    display: inline-flex;
    min-height: 28px;
    align-items: center;
    gap: 7px;
    margin-left: auto;
    color: var(--muted-strong);
    cursor: pointer;
    font-size: 0.72rem;
    font-weight: 600;
  }

  .component-match-toggle input {
    width: 15px;
    height: 15px;
    margin: 0;
    accent-color: var(--accent);
  }

  .paper-link {
    color: inherit;
    text-decoration: underline;
    text-decoration-color: hsl(var(--ink-hsl) / 0.3);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }

  .paper-link:hover,
  .paper-link:focus-visible {
    color: inherit;
    text-decoration-color: currentColor;
  }

  .dataset-cell .paper-link,
  .dataset-title-button {
    color: var(--ink);
  }

  .dataset-option-link,
  .dataset-name-toggle {
    overflow: hidden;
    color: var(--muted-strong);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-option-detail {
    width: 100%;
    min-width: 0;
    border: 0;
    background: transparent;
    padding: 0;
    font: inherit;
    text-align: left;
    text-decoration: underline;
    text-decoration-color: hsl(var(--ink-hsl) / 0.3);
    text-decoration-style: dotted;
    text-underline-offset: 3px;
    cursor: pointer;
  }

  .dataset-option-detail:hover,
  .dataset-option-detail:focus-visible {
    color: var(--ink);
    text-decoration-color: currentColor;
    outline: none;
  }

  .dataset-name-toggle {
    cursor: pointer;
  }

  .dataset-options {
    display: grid;
    padding: 4px 0;
  }

  .dataset-option {
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr);
    gap: 9px;
    align-items: center;
    min-height: 30px;
    padding: 0 10px;
    color: var(--muted-strong);
  }

  .dataset-option:hover {
    background: var(--panel-soft);
  }

  .dataset-option input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }

  .dataset-check {
    display: grid;
    width: 16px;
    height: 16px;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 4px;
    background: var(--panel);
  }

  .dataset-check::after {
    content: "";
    width: 7px;
    height: 4px;
    border-bottom: 2px solid var(--panel);
    border-left: 2px solid var(--panel);
    opacity: 0;
    transform: rotate(-45deg) translateY(-1px);
  }

  .dataset-option input:checked + .dataset-check {
    border-color: var(--accent-strong);
    background: var(--accent);
  }

  .dataset-option input:checked + .dataset-check::after {
    opacity: 1;
  }

  .dataset-option input:focus-visible + .dataset-check {
    outline: 2px solid hsl(var(--ink-hsl) / 0.28);
    outline-offset: 2px;
  }

  .table-wrap {
    min-width: 0;
    overflow: auto;
  }

  .leaderboard-wrap {
    overflow-x: hidden;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    border-bottom: 1px solid var(--line);
    text-align: left;
    vertical-align: middle;
  }

  .leaderboard-table {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    table-layout: auto;
  }

  .leaderboard-table th,
  .leaderboard-table td {
    min-width: 0;
    padding: 11px 8px;
    overflow-wrap: anywhere;
  }

  .leaderboard-table th {
    white-space: normal;
  }

  .leaderboard-table th:first-child,
  .leaderboard-table td:first-child {
    width: 1%;
  }

  .leaderboard-table th:nth-child(2),
  .leaderboard-table td:nth-child(2) {
    width: 30%;
  }

  .leaderboard-table th:last-child,
  .leaderboard-table td:last-child {
    text-align: left;
  }

  .efficiency-cell {
    min-width: 0;
  }

  .leaderboard-table tbody tr.clickable-row {
    cursor: pointer;
  }

  .leaderboard-table tbody tr:hover td {
    background: hsl(var(--panel-strong-hsl) / 0.72);
  }

  .leaderboard-table tbody tr.clickable-row:focus-visible {
    outline: 2px solid hsl(var(--ink-hsl) / 0.3);
    outline-offset: -2px;
  }

  .leaderboard-table tbody tr.clickable-row:focus-visible td {
    background: hsl(var(--panel-strong-hsl) / 0.72);
  }

  .sort-button {
    appearance: none;
    display: inline-flex;
    align-items: center;
    gap: 3px;
    min-width: 0;
    max-width: 100%;
    border: 0;
    background: transparent;
    color: inherit;
    padding: 0;
    font: inherit;
    text-align: left;
    text-transform: inherit;
    white-space: normal;
    cursor: pointer;
  }

  .metric-heading {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .heading-label {
    display: inline;
    min-width: 0;
    font: inherit;
    line-height: inherit;
    overflow-wrap: normal;
  }

  .info-tip {
    position: relative;
    display: inline-block;
    flex: 0 0 auto;
    color: inherit;
    cursor: help;
    font-family:
      "baselGrotesk", "Inter", ui-sans-serif, system-ui, -apple-system,
      BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1.05;
    text-transform: none;
    vertical-align: baseline;
  }

  .info-tip::after {
    position: absolute;
    top: calc(100% + 8px);
    left: 50%;
    z-index: 30;
    width: 248px;
    max-width: min(248px, 70vw);
    padding: 8px 10px;
    border: 1px solid var(--line-strong);
    border-radius: 7px;
    background: var(--ink);
    color: var(--panel);
    box-shadow: none;
    content: attr(data-tip);
    font-family:
      "baselGrotesk", "Inter", ui-sans-serif, system-ui, -apple-system,
      BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.74rem;
    font-weight: 500;
    line-height: 1.35;
    opacity: 0;
    pointer-events: none;
    text-align: left;
    text-transform: none;
    transform: translate(-50%, -2px);
    transition:
      opacity 120ms ease,
      transform 120ms ease;
    white-space: normal;
  }

  .info-tip::before {
    position: absolute;
    top: calc(100% + 4px);
    left: 50%;
    z-index: 31;
    width: 8px;
    height: 8px;
    background: var(--ink);
    content: "";
    opacity: 0;
    pointer-events: none;
    transform: translateX(-50%) rotate(45deg);
    transition: opacity 120ms ease;
  }

  .info-tip:hover::after,
  .info-tip:focus-visible::after,
  .info-tip:hover::before,
  .info-tip:focus-visible::before {
    opacity: 1;
    transform: translate(-50%, 0);
  }

  .info-tip:hover::before,
  .info-tip:focus-visible::before {
    transform: translateX(-50%) rotate(45deg);
  }

  .sort-button.active-sort {
    color: var(--ink);
  }

  .sort-glyph {
    display: inline-grid;
    align-self: center;
    align-content: center;
    gap: 2px;
    width: 6px;
    height: 12px;
    min-width: 6px;
    color: hsl(var(--ink-hsl) / 0.16);
    justify-items: center;
  }

  .sort-glyph span {
    display: block;
    width: 0;
    height: 0;
    min-width: 0;
    border-right: 3px solid transparent;
    border-left: 3px solid transparent;
    opacity: 1;
    transition:
      border-color 120ms ease,
      opacity 120ms ease;
  }

  .sort-glyph span:first-child {
    border-bottom: 3.5px solid currentColor;
  }

  .sort-glyph span:last-child {
    border-top: 3.5px solid currentColor;
  }

  .sort-glyph span.active-arrow {
    opacity: 1;
    color: var(--ink);
  }

  .sort-button.active-sort .sort-glyph span:not(.active-arrow) {
    color: hsl(var(--ink-hsl) / 0.18);
    opacity: 0.72;
  }

  .sort-button:not(.active-sort) .sort-glyph span {
    color: hsl(var(--ink-hsl) / 0.12);
    opacity: 0.62;
  }

  .sort-button:hover .sort-glyph span,
  .sort-button:focus-visible .sort-glyph span {
    color: hsl(var(--ink-hsl) / 0.32);
    opacity: 1;
  }

  .sort-button.active-sort:hover .sort-glyph span.active-arrow,
  .sort-button.active-sort:focus-visible .sort-glyph span.active-arrow {
    color: var(--ink);
  }

  .number,
  .net-cell {
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .number strong,
  .number span {
    display: block;
  }

  .number strong {
    color: var(--ink);
    font-size: 0.94rem;
    font-weight: 500;
  }

  .number strong.best-score {
    font-weight: 700;
  }

  .number span {
    font-size: 0.78rem;
  }

  .model-title-button {
    display: block;
    color: var(--ink);
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 1.2;
    text-decoration: underline;
    text-decoration-color: hsl(var(--ink-hsl) / 0.5);
    text-decoration-style: dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
    overflow-wrap: normal;
    white-space: nowrap;
  }

  .model-name-line {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .entity-marker {
    display: block;
    flex: 0 0 auto;
    width: 15px;
    height: 15px;
    overflow: visible;
    stroke: var(--panel);
    stroke-width: 1.25;
  }

  .clickable-row:hover .model-title-button,
  .clickable-row:focus-visible .model-title-button {
    text-decoration-color: currentColor;
    text-decoration-style: solid;
  }

  .institution-list {
    display: block;
    max-width: 164px;
    margin-top: 4px;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.25;
  }

  .institution-list span {
    color: inherit;
  }

  .net-visual {
    display: grid;
    grid-template-columns: minmax(54px, max-content) minmax(44px, 1fr);
    gap: 6px;
    align-items: center;
  }

  .net-score strong,
  .net-score span {
    display: block;
  }

  .net-score strong {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--positive-text);
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 1.1;
  }

  .net-score strong.best-score {
    font-weight: 700;
  }

  .net-score span {
    margin-top: 2px;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.1;
  }

  .net-cell.negative-score .net-score strong {
    color: var(--danger-text);
  }

  .net-direction {
    width: 0;
    height: 0;
    border-right: 3.5px solid transparent;
    border-bottom: 5px solid currentColor;
    border-left: 3.5px solid transparent;
    color: inherit;
  }

  .net-direction.down {
    border-top: 5px solid currentColor;
    border-bottom: 0;
  }

  .net-direction.flat {
    width: 7px;
    height: 2px;
    border: 0;
    background: currentColor;
  }

  .net-bar {
    position: relative;
    height: 16px;
    background: var(--panel-strong);
    overflow: visible;
  }

  .net-fill {
    position: absolute;
    top: 0;
    left: var(--net-fill-left, 50%);
    width: var(--net-fill-width, 0%);
    height: 100%;
    background: hsl(125 49% 43%);
  }

  .net-cell.negative-score .net-fill {
    background: hsl(2 63% 54%);
  }

  .net-zero {
    position: absolute;
    top: -2px;
    bottom: -2px;
    left: 50%;
    width: 1px;
    background: hsl(var(--ink-hsl) / 0.34);
  }

  .net-ci-line {
    position: absolute;
    top: 50%;
    left: var(--net-ci-left, 50%);
    width: var(--net-ci-width, 0%);
    height: 1.5px;
    background: hsl(var(--ink-hsl) / 0.55);
    transform: translateY(-50%);
  }

  .net-ci-cap {
    position: absolute;
    top: 3px;
    width: 1.5px;
    height: 10px;
    background: hsl(var(--ink-hsl) / 0.55);
    transform: translateX(-50%);
  }

  .net-ci-low {
    left: var(--net-ci-low, 50%);
  }

  .net-ci-high {
    left: var(--net-ci-high, 50%);
  }

  .family {
    color: var(--muted-strong);
  }

  .family-pill-list {
    display: flex;
    flex-wrap: wrap;
    gap: 5px 6px;
    align-items: center;
  }

  .family-pill {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    gap: 5px;
    min-height: 20px;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    background: var(--panel-soft);
    color: var(--ink);
    padding: 3px 8px;
    font-size: 0.7rem;
    font-weight: 600;
    line-height: 1.05;
    overflow-wrap: normal;
    text-align: center;
    max-width: 100%;
    overflow-wrap: anywhere;
    white-space: normal;
  }

  .family-pill-info {
    display: inline-block;
    flex: 0 0 auto;
    color: inherit;
    cursor: help;
    font-family:
      "baselGrotesk", "Inter", ui-sans-serif, system-ui, -apple-system,
      BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1.05;
    text-transform: none;
    vertical-align: baseline;
  }

  .family-pill-info:hover,
  .family-pill-info:focus-visible {
    color: var(--ink);
    outline: none;
  }

  .dataset-name-toggle .family-pill {
    min-height: 18px;
    font-size: 0.68rem;
  }

  .pending {
    color: var(--muted);
  }

  .matrix-wrap {
    max-height: none;
    background: var(--panel);
    overflow-x: auto;
    overflow-y: visible;
    overscroll-behavior-x: contain;
  }

  .matrix-table {
    width: 100%;
    margin: 0;
    table-layout: auto;
  }

  .matrix-table th,
  .matrix-table td {
    height: 30px;
    padding: 0 4px;
    border-right: 1px solid var(--line);
    text-align: center;
  }

  .matrix-table thead th {
    background: var(--panel);
  }

  .matrix-table thead th:not(.sticky-col) {
    width: auto;
    min-width: 58px;
    height: auto;
    padding-top: 8px;
    padding-bottom: 8px;
    vertical-align: middle;
  }

  .matrix-model-heading {
    position: relative;
    cursor: pointer;
  }

  .matrix-corner {
    position: sticky;
    min-width: 150px !important;
    padding: 0 !important;
    overflow: hidden;
  }

  .matrix-corner::after {
    position: absolute;
    inset: 0;
    z-index: 0;
    background: linear-gradient(
      to top right,
      transparent calc(50% - 0.75px),
      var(--line-strong) calc(50% - 0.75px),
      var(--line-strong) calc(50% + 0.75px),
      transparent calc(50% + 0.75px)
    );
    content: "";
    pointer-events: none;
  }

  .matrix-table thead th .matrix-corner-label {
    position: absolute;
    z-index: 1;
    color: var(--muted-strong);
    font-size: 0.68rem;
    font-weight: 600;
    line-height: 1;
    text-transform: uppercase;
    white-space: nowrap;
    writing-mode: horizontal-tb;
    transform: none;
  }

  .matrix-corner-models {
    top: 12px;
    right: 10px;
  }

  .matrix-corner-datasets {
    bottom: 12px;
    left: 10px;
  }

  .matrix-mean-heading,
  .matrix-mean-cell {
    border-left: 2px solid var(--line-strong) !important;
  }

  .matrix-table thead th span {
    display: inline-block;
    color: var(--muted-strong);
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.15;
    text-transform: none;
    white-space: nowrap;
    writing-mode: vertical-rl;
    max-height: none;
    overflow: visible;
    transform: rotate(180deg);
  }

  .matrix-model-button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 0;
    background: transparent;
    color: inherit;
    padding: 0;
    font: inherit;
    text-align: inherit;
    text-decoration: underline;
    text-decoration-color: hsl(var(--ink-hsl) / 0.5);
    text-decoration-style: dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
    cursor: pointer;
  }

  .matrix-model-marker {
    width: 13px;
    height: 13px;
    transform: rotate(180deg);
  }

  .matrix-model-heading:hover .matrix-model-button,
  .matrix-model-button:hover,
  .matrix-model-button:focus-visible {
    color: var(--ink);
    text-decoration-color: currentColor;
    text-decoration-style: solid;
  }

  .matrix-model-button:focus-visible {
    outline: 2px solid hsl(var(--ink-hsl) / 0.28);
    outline-offset: 3px;
  }

  .matrix-table td {
    width: auto;
    min-width: 58px;
    background: var(--score-bg, transparent);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .matrix-table td strong,
  .matrix-table td span,
  .dataset-title-button,
  .dataset-cell .paper-link,
  .dataset-cell span {
    display: block;
  }

  .matrix-table td strong {
    color: var(--ink);
    font-size: 0.94rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 30px;
  }

  .matrix-table td span,
  .dataset-cell span {
    font-size: 0.72rem;
  }

  .matrix-table .pending-cell {
    background: hsl(var(--panel-strong-hsl) / 0.72);
  }

  .matrix-table .pending-cell strong {
    color: var(--muted);
  }

  .matrix-summary-row th,
  .matrix-summary-row td {
    border-top: 2px solid var(--line-strong);
  }

  .matrix-summary-label {
    color: var(--ink);
    font-family: inherit;
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 30px;
  }

  .sticky-col {
    position: sticky;
    left: 0;
    z-index: 2;
    width: 1% !important;
    min-width: max-content !important;
    background: var(--panel);
  }

  .matrix-table thead .sticky-col {
    z-index: 3;
  }

  .dataset-cell {
    height: 30px;
    padding: 0 12px !important;
    text-align: left !important;
    text-transform: none;
    white-space: nowrap;
  }

  .dataset-title-button {
    width: 100%;
    border: 0;
    background: transparent;
    color: var(--ink);
    overflow: hidden;
    padding: 0;
    font-size: 0.94rem;
    font-weight: 500;
    font-family: inherit;
    line-height: 30px;
    text-align: left;
    text-decoration: underline;
    text-decoration-color: hsl(var(--ink-hsl) / 0.5);
    text-decoration-style: dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
    text-overflow: ellipsis;
    text-transform: none;
    white-space: nowrap;
    cursor: pointer;
  }

  .matrix-dataset-title-button {
    display: inline-flex !important;
    align-items: center;
    gap: 7px;
  }

  .matrix-dataset-marker {
    width: 14px;
    height: 14px;
  }

  .dataset-cell:hover .dataset-title-button,
  .dataset-title-button:hover,
  .dataset-title-button:focus-visible {
    text-decoration-color: currentColor;
    text-decoration-style: solid;
  }

  .dataset-title-button:focus-visible {
    outline: 2px solid hsl(var(--ink-hsl) / 0.28);
    outline-offset: -2px;
  }

  .scatter-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    padding: 16px;
    align-items: stretch;
  }

  .pareto-grid {
    grid-template-columns: minmax(0, 1fr);
    padding-top: 8px;
  }

  .pareto-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: end;
    justify-content: flex-end;
  }

  .pareto-field {
    display: grid;
    gap: 5px;
  }

  .pareto-field-label {
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .pareto-metric-field {
    width: 220px;
  }

  .pareto-scale-field {
    width: 132px;
  }

  .pareto-select {
    position: relative;
    display: block;
  }

  .pareto-select::after {
    position: absolute;
    top: 50%;
    right: 12px;
    width: 7px;
    height: 7px;
    border-right: 1.5px solid var(--muted);
    border-bottom: 1.5px solid var(--muted);
    content: "";
    pointer-events: none;
    transform: translateY(-70%) rotate(45deg);
  }

  .pareto-select select {
    width: 100%;
    min-height: 36px;
    appearance: none;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel-soft);
    color: var(--ink);
    padding: 0 34px 0 10px;
    font: inherit;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .pareto-select select:hover {
    border-color: var(--accent);
    background: var(--panel);
  }

  .pareto-select select:focus-visible {
    outline: 2px solid hsl(var(--ink-hsl) / 0.28);
    outline-offset: 2px;
  }

  .frontier-toggle {
    display: inline-flex;
    min-height: 36px;
    align-items: center;
    gap: 8px;
    color: var(--ink);
    cursor: pointer;
  }

  .frontier-toggle input {
    width: 16px;
    height: 16px;
    accent-color: var(--accent);
  }

  .frontier-toggle span {
    color: var(--ink) !important;
    font-size: 0.8rem !important;
    text-transform: none !important;
  }

  .scatter-plot {
    display: grid;
    min-width: 0;
    gap: 8px;
    align-content: start;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel);
    padding: 12px;
  }

  .scatter-plot h3 {
    margin: 0;
    color: var(--ink);
    font-family: var(--display-serif);
    font-size: 1rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.15;
  }

  .pareto-plot {
    border: 0;
    border-radius: 0;
    padding: 0;
  }

  .pareto-plot h3 {
    font-size: 1.1rem;
  }

  .scatter-chart {
    display: block;
    width: 100%;
    height: auto;
    background: var(--panel);
    overflow: visible;
  }

  .scatter-grid-lines line {
    stroke: hsl(var(--ink-hsl) / 0.1);
    stroke-width: 1;
  }

  .scatter-axis line {
    stroke: var(--ink);
    stroke-width: 1.15;
  }

  .scatter-ticks line {
    stroke: hsl(var(--ink-hsl) / 0.4);
    stroke-width: 1;
  }

  .scatter-ticks text,
  .scatter-axis-title {
    fill: var(--muted-strong);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 9px;
    font-weight: 500;
  }

  .pareto-frontier {
    fill: none;
    stroke: var(--ink);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 6 4;
  }

  .scatter-axis-title {
    fill: var(--ink);
    font-size: 9.4px;
  }

  .scatter-point {
    cursor: pointer;
    outline: none;
  }

  .scatter-marker-shape {
    stroke: var(--panel);
    stroke-width: 1.6;
    transition:
      opacity 120ms ease,
      stroke-width 120ms ease;
  }

  .scatter-point.dominated-point .scatter-marker-shape {
    opacity: 0.52;
  }

  .scatter-point.pareto-point .scatter-marker-shape {
    stroke: var(--ink);
    stroke-width: 2.2;
  }

  .scatter-point:hover .scatter-marker-shape,
  .scatter-point:focus-visible .scatter-marker-shape {
    opacity: 1;
    stroke: var(--ink);
    stroke-width: 3;
  }

  .scatter-tooltip {
    position: fixed;
    z-index: 90;
    display: grid;
    gap: 2px;
    width: max-content;
    max-width: min(19rem, calc(100vw - 24px));
    padding: 0.55rem 0.65rem;
    transform: translate(-50%, calc(-100% - 0.55rem));
    border: 1px solid var(--ink);
    border-radius: 8px;
    background: var(--ink);
    color: var(--panel);
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.2;
    pointer-events: none;
    text-align: left;
    white-space: normal;
  }

  .component-tooltip {
    position: fixed;
    z-index: 120;
    width: max-content;
    max-width: min(19rem, calc(100vw - 24px));
    padding: 0.55rem 0.65rem;
    transform: translate(-50%, calc(-100% - 0.55rem));
    border: 1px solid var(--ink);
    border-radius: 8px;
    background: var(--ink);
    color: var(--panel);
    font-size: 0.74rem;
    font-weight: 500;
    line-height: 1.35;
    pointer-events: none;
    text-align: left;
    white-space: normal;
  }

  .scatter-tooltip strong {
    color: var(--panel);
    font-size: 0.78rem;
  }

  .scatter-tooltip span {
    color: hsl(var(--panel-strong-hsl) / 0.78);
    font-weight: 500;
  }

  .scatter-tooltip .pareto-status {
    color: hsl(85 56% 72%);
    font-weight: 700;
  }

  .empty-view {
    padding: 36px 16px;
    color: var(--muted);
    text-align: center;
  }

  .modal-layer {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: grid;
    place-items: center;
    padding: 24px;
  }

  .modal-backdrop {
    position: absolute;
    inset: 0;
    border: 0;
    background: hsl(var(--ink-hsl) / 0.28);
    cursor: pointer;
  }

  .model-modal {
    position: relative;
    z-index: 1;
    display: grid;
    gap: 16px;
    width: min(760px, calc(100vw - 32px));
    max-height: min(760px, calc(100vh - 32px));
    overflow: auto;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel);
    box-shadow: none;
    padding: 18px;
  }

  .model-modal-header {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: start;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--line);
  }

  .modal-close {
    position: relative;
    display: grid;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    background: var(--panel-soft);
    color: var(--ink);
    cursor: pointer;
    padding: 0;
  }

  .modal-close::before,
  .modal-close::after {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 13px;
    height: 1.5px;
    border-radius: 999px;
    background: currentColor;
    content: "";
    transform-origin: center;
  }

  .modal-close::before {
    transform: translate(-50%, -50%) rotate(45deg);
  }

  .modal-close::after {
    transform: translate(-50%, -50%) rotate(-45deg);
  }

  .modal-close:hover,
  .modal-close:focus-visible {
    background: var(--panel);
    outline: 2px solid hsl(var(--ink-hsl) / 0.2);
    outline-offset: 2px;
  }

  .detail-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .dataset-detail-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .detail-metrics div {
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel-soft);
    padding: 12px;
  }

  .detail-metrics span {
    display: block;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .detail-metrics strong {
    display: block;
    margin-top: 8px;
    color: var(--ink);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 1.25rem;
    font-weight: 600;
  }

  .model-size-note {
    margin: 2px 0 0;
    color: var(--muted);
    font-size: 0.8rem;
    line-height: 1.35;
  }

  .model-size-note strong {
    font-weight: 600;
  }

  .dataset-detail-metrics strong {
    font-size: 0.98rem;
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .detail-section h3 {
    color: var(--ink);
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  .detail-section {
    display: grid;
    gap: 10px;
  }

  .modal-paper-title {
    display: inline-flex;
    align-items: flex-start;
    gap: 7px;
    width: fit-content;
    max-width: min(560px, 100%);
    margin-top: 7px;
    color: var(--ink);
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.3;
    text-decoration: underline;
    text-decoration-color: hsl(var(--ink-hsl) / 0.3);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }

  .modal-paper-title:hover,
  .modal-paper-title:focus-visible {
    text-decoration-color: currentColor;
    outline: none;
  }

  .modal-paper-title.pending {
    color: var(--muted-strong);
    text-decoration: none;
  }

  .paper-title-icon {
    display: inline-flex;
    flex: 0 0 auto;
    width: 15px;
    height: 15px;
    margin-top: 1px;
    color: inherit;
  }

  .paper-title-icon svg {
    display: block;
    width: 15px;
    height: 15px;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.7;
  }

  .author-list {
    display: grid;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .author-list li {
    display: grid;
    gap: 3px;
    border-bottom: 1px solid var(--line);
    padding-bottom: 8px;
  }

  .author-list li:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }

  .author-list strong {
    color: var(--ink);
    font-size: 0.9rem;
    font-weight: 600;
  }

  .author-list span {
    color: var(--muted-strong);
    font-size: 0.82rem;
    line-height: 1.35;
  }

  .modal-author-list {
    max-width: min(620px, 100%);
    margin-top: 10px;
    gap: 6px;
  }

  .modal-author-list li {
    padding-bottom: 6px;
  }

  @media (max-width: 900px) {
    .scatter-grid {
      grid-template-columns: 1fr;
    }

  }

  @media (max-width: 760px) {
    .panel-header {
      display: grid;
      align-items: start;
    }

    .filter-content {
      grid-template-columns: 1fr;
    }

    .view-switcher button {
      min-height: 52px;
      padding: 5px 3px;
      font-size: 0.66rem;
      overflow-wrap: anywhere;
      font-size: 0.68rem;
      line-height: 1.18;
    }

    .view-switcher {
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }

    .pareto-controls {
      width: 100%;
      align-items: stretch;
      justify-content: start;
    }

    .pareto-controls label:not(.frontier-toggle) {
      width: 100%;
    }

    .pareto-controls select {
      width: 100%;
    }

    .dataset-filter {
      width: 100%;
    }

    .dataset-menu {
      position: static;
      width: 100%;
      max-height: 340px;
      margin-top: 6px;
    }

    .leaderboard-table th,
    .leaderboard-table td {
      padding-right: 4px;
      padding-left: 4px;
    }

    .dataset-cell {
      padding: 0 8px !important;
    }

    .dataset-title-button {
      font-size: 0.86rem;
    }

    .matrix-table td strong {
      font-size: 0.86rem;
    }

    .scatter-grid {
      gap: 14px;
      padding: 12px 8px;
    }

    .scatter-plot h3 {
      font-size: 0.92rem;
    }

    .modal-layer {
      padding: 12px;
    }

    .model-modal {
      width: calc(100vw - 24px);
      max-height: calc(100vh - 24px);
      padding: 14px;
    }

    .detail-metrics {
      grid-template-columns: 1fr;
    }
  }
  .deployment-section {
    padding: 14px 16px;
  }

  .deployment-section h3 {
    margin: 0 0 8px;
    font-size: 0.95rem;
  }

  .deployment-summary td,
  .deployment-summary th {
    white-space: nowrap;
    text-align: right;
    padding: 6px 10px;
  }

  .deployment-summary th:first-child,
  .deployment-summary td:first-child {
    text-align: left;
  }

  .deployment-summary .group-heading {
    text-align: center;
    border-bottom: 1px solid var(--line);
  }

  .deployment-summary .dataset-title-button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .deployment-summary .entity-marker {
    flex: none;
    margin: 0;
  }

  .deployment-summary .heat-cell {
    background: var(--score-bg, transparent);
    border-bottom: 1px solid var(--panel);
  }

  .deployment-summary .group-start-true {
    border-left: 3px solid var(--panel);
  }

  .deployment-summary .few-fits {
    opacity: 0.5;
  }

  .deployment-flag {
    color: var(--muted, #6b6963);
    font-weight: 500;
  }

  #best-view .view-note,
  #gap-view .view-note {
    padding: 0 16px 14px;
  }

  .filter-inactive {
    opacity: 0.45;
  }

  .filter-inactive select {
    cursor: not-allowed;
  }

  .family-tag-list {
    gap: 4px;
  }

  .family-tag {
    padding: 2px 7px;
    overflow-wrap: normal;
    white-space: nowrap;
    cursor: help;
  }

  .phone-tags,
  .phone-results {
    display: none;
  }

  .scatter-labels text {
    fill: var(--ink);
    font-size: 13px;
    font-weight: 600;
    paint-order: stroke;
    stroke: var(--panel);
    stroke-width: 3px;
    stroke-linejoin: round;
    pointer-events: none;
  }

  .scatter-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 12px;
    margin: 4px 0 0;
    padding: 0;
    list-style: none;
  }

  .scatter-legend button {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border: 0;
    background: transparent;
    color: var(--muted-strong);
    padding: 2px 0;
    font: inherit;
    font-size: 0.76rem;
    cursor: pointer;
  }

  .scatter-legend button:hover,
  .scatter-legend button:focus-visible {
    color: var(--ink);
    text-decoration: underline;
  }

  .scatter-legend .on-front button {
    color: var(--ink);
    font-weight: 700;
  }

  .scatter-legend .entity-marker {
    flex: none;
    margin: 0;
  }

  @media (max-width: 760px) {
    .leaderboard-table th:nth-child(2),
    .leaderboard-table td:nth-child(2),
    .leaderboard-table th:nth-child(3),
    .leaderboard-table td:nth-child(3),
    .leaderboard-table th:nth-child(n + 6),
    .leaderboard-table td:nth-child(n + 6) {
      display: none;
    }

    .leaderboard-table th:first-child,
    .leaderboard-table td:first-child {
      white-space: normal;
    }

    .leaderboard-table .institution-list {
      display: none;
    }

    .leaderboard-table .model-name-line,
    .leaderboard-table .model-title-button {
      min-width: 0;
      white-space: normal;
      overflow-wrap: normal;
    }

    .leaderboard-table th,
    .leaderboard-table td {
      min-width: 0;
      padding-right: 5px;
      padding-left: 5px;
      overflow-wrap: normal;
    }

    .leaderboard-table th:first-child,
    .leaderboard-table td:first-child {
      width: 50%;
    }

    .leaderboard-table th:nth-child(n + 4),
    .leaderboard-table td:nth-child(n + 4) {
      width: 25%;
    }

    .phone-tags {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 0.7rem;
    }

    .phone-results {
      display: grid;
    }

    .scatter-labels text {
      font-size: 20px;
    }
  }

  .matrix-note {
    padding: 0 16px 14px;
  }

  .view-note {
    margin: 10px 0 0;
    color: var(--muted, #6b6963);
    font-size: 0.82rem;
    line-height: 1.45;
  }

  .gap-chart {
    display: block;
    width: 100%;
    min-width: 860px;
    height: auto;
  }

  .gap-chart text {
    fill: currentColor;
    font-size: 11px;
  }

  .gap-grid line {
    stroke: var(--line);
  }

  .gap-range {
    fill: currentColor;
    opacity: 0.12;
  }

  .gap-mean {
    stroke: currentColor;
    stroke-width: 2.5;
  }

  .gap-chart .gap-summary-labels text {
    font-size: 10px;
    opacity: 0.75;
  }

  .gap-chart .gap-mean-label {
    font-size: 9.5px;
    opacity: 0.75;
  }

  .gap-dot:hover,
  .gap-dot:focus-visible {
    stroke: currentColor;
    stroke-width: 1.5;
    outline: none;
  }
  .pareto-membership {
    padding: 8px 16px 16px;
  }

  .pareto-membership h3 {
    margin: 0 0 8px;
    color: var(--ink);
    font-family: var(--display-serif);
    font-size: 1.1rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.15;
  }

</style>
