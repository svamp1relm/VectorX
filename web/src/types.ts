// TypeScript mirrors of api/serialization.py's JSON shapes. The frontend
// never recomputes anything — these are read-only view models.

export interface HistogramBins {
  edges: number[]
  counts: number[]
}

export interface ExperimentSummary {
  runs: number
  mean_total_return: number
  median_total_return: number
  stdev_total_return: number
  p_negative: number
  p_ruined: number
  total_return_histogram: HistogramBins
  r_multiple_histogram: HistogramBins
  expectancy: ExpectancyComparison | null
}

export interface ExperimentModelSpec {
  p_win: number
  win_r: number
  loss_r: number
  n_trades: number
  risk_unit_fraction: number
}

export interface RiskDefinition {
  unit: 'R'
  normalization_version: 'r-v1'
  method: 'model_r' | 'entry_price_stop_loss_fraction'
  risk_unit_fraction: number
  cost_basis: 'gross_r'
}

export interface ExpectancyEstimate {
  value: number
  canonical_value: number | null
  source: 'theoretical_model' | 'monte_carlo_sample' | 'historical_backtest'
  unit: 'R'
  sample_size: number | null
  planned_sample_size: number | null
  risk_definition: RiskDefinition
}

export interface ExpectancyComparison {
  theoretical: ExpectancyEstimate | null
  sample: ExpectancyEstimate | null
  historical: ExpectancyEstimate | null
}

export interface RiskCompatibility {
  compatible: boolean
  same_risk_definition: boolean
  reference_risk_fraction: number
  mismatches: string[]
}

export interface ComparisonDeltas {
  delta_theoretical_sample: number | null
  delta_theoretical_historical: number | null
  delta_sample_historical: number | null
}

export interface ExpectancyComparisonResult {
  estimates: ExpectancyComparison
  risk_compatibility: RiskCompatibility
  deltas: ComparisonDeltas
  warnings: string[]
}

export interface ExperimentPortfolioSpec {
  initial_capital: number
  risk_per_trade: number
  commission: number
  slippage: number
}

export interface MonteCarloExperimentSpec {
  type: 'monte_carlo'
  name: string
  seed: number
  runs: number
  model: ExperimentModelSpec
  portfolio: ExperimentPortfolioSpec
  storage: { store_trades: boolean }
}

export interface HistoricalDataSpec {
  source: string
  path: string
  symbol: string
  timeframe: string
}

interface StrategyRiskSpec {
  stop_loss_pct: number
}

export interface MovingAverageCrossoverStrategySpec extends StrategyRiskSpec {
  type: 'moving_average_crossover'
  fast_period: number
  slow_period: number
}

export interface BuyAndHoldStrategySpec extends StrategyRiskSpec {
  type: 'buy_and_hold'
}

export interface RandomEntryStrategySpec extends StrategyRiskSpec {
  type: 'random_entry'
  entry_probability: number
  exit_probability: number
}

export interface BreakoutStrategySpec extends StrategyRiskSpec {
  type: 'breakout'
  entry_lookback: number
  exit_lookback: number
}

export type HistoricalStrategySpec =
  | MovingAverageCrossoverStrategySpec
  | BuyAndHoldStrategySpec
  | RandomEntryStrategySpec
  | BreakoutStrategySpec

export interface HistoricalBacktestExperimentSpec {
  type: 'historical_backtest'
  name: string
  seed: number
  runs: number
  data: HistoricalDataSpec
  strategy: HistoricalStrategySpec
  portfolio: ExperimentPortfolioSpec
  storage: { store_trades: boolean }
}

// Mirrors vectorx.experiments.spec's discriminated union (Фаза 16a) — narrow
// on `spec.type` before accessing `model`/`data`/`strategy`.
export type ExperimentSpec = MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec

export interface ExperimentSummaryItem {
  id: number
  name: string
  spec_type: 'monte_carlo' | 'historical_backtest'
  seed: number
  runs: number
  status: string
  created_at: string
  experiment_version: number
  code_version: string
  mean_total_return: number
  median_total_return: number
  stdev_total_return: number
  p_negative: number
  p_ruined: number
}

export interface ExperimentDetail {
  id: number
  name: string
  seed: number
  runs: number
  status: string
  created_at: string
  duration: number
  experiment_version: number
  code_version: string
  spec: ExperimentSpec
  summary: ExperimentSummary
}

// `profit_factor` can be the string "Infinity"/"-Infinity"/"NaN" (see
// api/serialization.py — JSON has no Infinity literal). `expectancy_theoretical`
// is `null` for historical backtest runs (no p_win/win_r/loss_r model exists).
export interface Metrics {
  trades: number
  wins: number
  losses: number
  win_rate: number | null
  avg_win: number | null
  avg_loss: number | null
  expectancy_theoretical: number | null
  expectancy_sample: number | null
  total_return: number
  avg_trade: number | null
  variance: number | null
  stdev: number | null
  max_drawdown: number
  profit_factor: number | string | null
  ruined: boolean
  expectancy_sample_net?: number | null
  win_rate_net?: number | null
  profit_factor_net?: number | string | null
}

export interface EquityPoint {
  index: number
  equity: number
  drawdown: number
}

export interface RunResult {
  run_index: number
  derived_seed: number
  metrics: Metrics
  equity_curve?: EquityPoint[]
}

export interface ConfidenceInterval {
  point_estimate: number
  lower: number
  upper: number
  confidence: number
  n_resamples: number
}

export interface RiskAdjustedMetrics {
  sharpe: number | null
  sortino: number | null
  calmar: number | null
}

export interface AnalysisResult {
  analysis_version: number
  confidence_interval: ConfidenceInterval
  risk_adjusted: RiskAdjustedMetrics
  significance_vs_zero: { ci: ConfidenceInterval; significant: boolean }
  confidence_interval_net?: ConfidenceInterval
  risk_adjusted_net?: RiskAdjustedMetrics
  significance_vs_zero_net?: { ci: ConfidenceInterval; significant: boolean }
  calmar_by_run?: { run_index: number; calmar: number | null }[]
}

export interface BatchSummary {
  id: number
  hypothesis: string
  notes: string | null
  created_at: string
  experiment_count: number
}

export interface BatchDetail {
  id: number
  hypothesis: string
  notes: string | null
  created_at: string
  experiments: ExperimentSummaryItem[]
}

export interface BatchCreateRequest {
  hypothesis: string
  notes?: string | null
  base: ExperimentSpec
  grid: Record<string, unknown[]>
}

export interface OutOfSampleRequest {
  base: HistoricalBacktestExperimentSpec
  train_start: string
  train_end: string
  test_start: string
  test_end: string
}

export interface ExpectancyEstimateLite {
  value: number
  canonical_value: number | null
  source: string
  sample_size: number | null
}

export interface OutOfSampleExperimentView {
  name: string
  seed: number
  runs: number
  status: string
  spec: ExperimentSpec
  summary: ExperimentSummary
  data_version?: string
  source_data_version?: string
  time_range?: { start: string; end: string }
  warmup_start?: string
  executable_spec?: boolean
}

export interface OutOfSampleResult {
  train: OutOfSampleExperimentView
  test: OutOfSampleExperimentView
  comparison: {
    train: ExpectancyEstimateLite | null
    test: ExpectancyEstimateLite | null
    risk_compatibility: RiskCompatibility
    delta_train_test: number | null
    warnings: string[]
  }
}

export interface SensitivityRequest {
  hypothesis: string
  base: ExperimentSpec
  grid: Record<string, unknown[]>
}

export interface SensitivityPoint {
  params: Record<string, unknown>
  expectancy_sample: number | null
  sharpe: number | null
  expectancy_sample_net?: number | null
  sharpe_net?: number | null
}

export interface SensitivityResult {
  analysis_version: number
  points: SensitivityPoint[]
}

export interface WalkForwardRequest {
  base: HistoricalBacktestExperimentSpec
  start: string
  end: string
  train_window_days: number
  test_window_days: number
  step_days: number
  reference_risk_fraction: number
}

export interface WalkForwardWindowResult {
  window: {
    train_start: string
    train_end: string
    test_start: string
    test_end: string
  }
  result: OutOfSampleResult
}

export interface WalkForwardResult {
  analysis_version: number
  windows: WalkForwardWindowResult[]
}

export interface BlockBootstrapRequest {
  blockSize: number
  seed: number
  confidence: number
  nResamples: number
  costBasis?: 'gross_r' | 'net_r'
}

export interface BlockBootstrapResult {
  analysis_version: number
  block_size: number
  cost_basis?: 'gross_r' | 'net_r'
  confidence_interval: ConfidenceInterval
}
