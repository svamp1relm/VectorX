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
}

export interface ExperimentModelSpec {
  p_win: number
  win_r: number
  loss_r: number
  n_trades: number
}

export interface ExperimentPortfolioSpec {
  initial_capital: number
  risk_per_trade: number
  commission: number
  slippage: number
}

export interface ExperimentSpec {
  name: string
  seed: number
  runs: number
  model: ExperimentModelSpec
  portfolio: ExperimentPortfolioSpec
  storage: { store_trades: boolean }
}

export interface ExperimentSummaryItem {
  id: number
  name: string
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
// api/serialization.py — JSON has no Infinity literal).
export interface Metrics {
  trades: number
  wins: number
  losses: number
  win_rate: number
  avg_win: number
  avg_loss: number
  expectancy_theoretical: number
  expectancy_sample: number
  total_return: number
  avg_trade: number
  variance: number
  stdev: number
  max_drawdown: number
  profit_factor: number | string
  ruined: boolean
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
