import { ref } from 'vue'

export type Locale = 'en' | 'ru'
export type Theme = 'light' | 'dark'

const localeKey = 'vectorx.locale'
const themeKey = 'vectorx.theme'

const messages: Record<Locale, Record<string, string>> = {
  en: {
    'app.title': 'VectorX',
    'app.subtitle': 'Research simulation lab',
    'controls.language': 'Language',
    'controls.theme': 'Theme',
    'controls.english': 'EN',
    'controls.russian': 'RU',
    'controls.light': 'Light',
    'controls.dark': 'Dark',
    'actions.back': 'Back',
    'state.loading': 'Loading…',
    'state.noExperiments': 'No experiments yet.',
    'state.noRuns': 'No runs.',
    'list.title': 'Experiments',
    'table.name': 'Name',
    'table.seed': 'Seed',
    'table.runs': 'Runs',
    'table.status': 'Status',
    'table.meanReturn': 'Mean total return',
    'table.negativeProbability': 'P(negative)',
    'table.ruinedProbability': 'P(ruined)',
    'detail.parameters': 'Parameters',
    'detail.type': 'Type',
    'detail.seed': 'Seed',
    'detail.pWin': 'p_win',
    'detail.winR': 'win_r',
    'detail.lossR': 'loss_r',
    'detail.nTrades': 'n_trades',
    'detail.riskUnitFraction': 'risk_unit_fraction',
    'detail.initialCapital': 'initial_capital',
    'detail.riskPerTrade': 'risk_per_trade',
    'detail.summary': 'Summary',
    'detail.runs': 'Runs',
    'detail.finalCapital': 'Final capital',
    'detail.totalTrades': 'Total trades',
    'detail.meanReturn': 'Mean total return',
    'detail.medianReturn': 'Median total return',
    'detail.stdevReturn': 'Stdev total return',
    'detail.negativeProbability': 'P(negative)',
    'detail.ruinedProbability': 'P(ruined)',
    'detail.equity': 'Equity',
    'detail.totalReturnDistribution': 'Total return distribution',
    'detail.rMultipleDistribution': 'R-multiple distribution',
    'detail.historicalRunNote': 'Runs is 1 because a historical backtest replays one fixed dataset once and is deterministic. Additional runs are only meaningful for Monte Carlo experiments, where random samples estimate a distribution.',
    'runs.run': 'Run',
    'runs.trades': 'Trades',
    'runs.winRate': 'Win rate',
    'runs.expectancy': 'Expectancy (sample)',
    'runs.totalReturn': 'Total return',
    'runs.maxDrawdown': 'Max drawdown',
    'runs.profitFactor': 'Profit factor',
    'runs.ruined': 'Ruined',
    'charts.equity': 'Equity',
    'comparison.title': 'Expectancy comparison',
    'comparison.description': 'Values are converted to the selected reference risk unit before deltas are calculated.',
    'comparison.counterpart': 'Comparison experiment',
    'comparison.referenceRisk': 'Reference risk fraction',
    'comparison.compare': 'Compare',
    'comparison.noCounterpart': 'No compatible experiment type is available.',
    'comparison.estimate': 'Estimate',
    'comparison.sourceValue': 'Source value',
    'comparison.referenceValue': 'Reference value',
    'comparison.sampleSize': 'Actual / planned trades',
    'comparison.riskUnitFraction': 'Source 1R fraction',
    'comparison.theoretical': 'Theoretical',
    'comparison.sample': 'Monte Carlo',
    'comparison.historical': 'Historical',
    'comparison.delta': 'Delta',
    'comparison.deltaTheoreticalSample': 'Theoretical − Monte Carlo',
    'comparison.deltaTheoreticalHistorical': 'Theoretical − Historical',
    'comparison.deltaSampleHistorical': 'Monte Carlo − Historical',
    'comparison.convertedWarning': 'Risk definitions differ. Values were converted to the selected common reference scale.',
    'comparison.incompatibleWarning': 'Risk definitions cannot be converted safely. Deltas are unavailable.',
    'type.monte_carlo': 'Monte Carlo',
    'type.historical_backtest': 'Historical backtest',
    'status.completed': 'Completed',
    'status.pending': 'Pending',
    'status.failed': 'Failed',
    'param.data.source': 'data.source',
    'param.data.path': 'data.path',
    'param.data.symbol': 'data.symbol',
    'param.data.timeframe': 'data.timeframe',
    'param.strategy.type': 'strategy.type',
    'param.strategy.fast_period': 'strategy.fast_period',
    'param.strategy.slow_period': 'strategy.slow_period',
    'param.strategy.stop_loss_pct': 'strategy.stop_loss_pct',
    'param.portfolio.initial_capital': 'portfolio.initial_capital',
    'param.portfolio.risk_per_trade': 'portfolio.risk_per_trade',
    'param.portfolio.commission': 'portfolio.commission',
    'param.portfolio.slippage': 'portfolio.slippage',
    'batches.title': 'Batches',
    'batches.empty': 'No batches yet.',
    'batches.hypothesis': 'Hypothesis',
    'batches.notes': 'Notes',
    'batches.experimentCount': 'Experiments',
    'batches.createTitle': 'Create batch',
    'batches.grid': 'Parameter grid (JSON)',
    'batches.create': 'Create',
    'batches.missingFieldsError': 'Fill in base experiment id and hypothesis before creating',
    'batches.invalidGridError': 'Parameter grid must be valid JSON, e.g. {"strategy.fast_period": [8, 10]}',
    'detail.analysis': 'Statistical analysis',
    'detail.expectancyCi': 'Expectancy 95% CI',
    'detail.significantVsZero': 'Significant vs zero',
    'detail.sharpe': 'Sharpe',
    'detail.sortino': 'Sortino',
    'detail.calmar': 'Calmar',
    'detail.exportJson': 'Export JSON',
    'detail.exportMarkdown': 'Export Markdown',
    'oos.title': 'Out-of-Sample',
    'oos.baseExperimentId': 'Base experiment id',
    'oos.trainStart': 'Train start',
    'oos.trainEnd': 'Train end',
    'oos.testStart': 'Test start',
    'oos.testEnd': 'Test end',
    'oos.run': 'Run',
    'oos.train': 'Train',
    'oos.test': 'Test',
    'oos.deltaTrainTest': 'Train − Test',
    'oos.notHistoricalError': 'Out-of-Sample requires a historical_backtest experiment',
    'oos.missingDatesError': 'Fill in train start/end and test start/end before running',
  },
  ru: {
    'app.title': 'VectorX',
    'app.subtitle': 'Лаборатория исследовательских симуляций',
    'controls.language': 'Язык',
    'controls.theme': 'Тема',
    'controls.english': 'EN',
    'controls.russian': 'RU',
    'controls.light': 'Светлая',
    'controls.dark': 'Тёмная',
    'actions.back': 'Назад',
    'state.loading': 'Загрузка…',
    'state.noExperiments': 'Экспериментов пока нет.',
    'state.noRuns': 'Прогонов нет.',
    'list.title': 'Эксперименты',
    'table.name': 'Название',
    'table.seed': 'Seed',
    'table.runs': 'Прогоны',
    'table.status': 'Статус',
    'table.meanReturn': 'Средняя доходность',
    'table.negativeProbability': 'P(убыток)',
    'table.ruinedProbability': 'P(разорение)',
    'detail.parameters': 'Параметры',
    'detail.type': 'Тип',
    'detail.seed': 'Seed',
    'detail.pWin': 'p_win',
    'detail.winR': 'win_r',
    'detail.lossR': 'loss_r',
    'detail.nTrades': 'n_trades',
    'detail.riskUnitFraction': 'risk_unit_fraction',
    'detail.initialCapital': 'начальный капитал',
    'detail.riskPerTrade': 'риск на сделку',
    'detail.summary': 'Сводка',
    'detail.runs': 'Прогоны',
    'detail.finalCapital': 'Итоговый капитал',
    'detail.totalTrades': 'Всего сделок',
    'detail.meanReturn': 'Средняя доходность',
    'detail.medianReturn': 'Медианная доходность',
    'detail.stdevReturn': 'Стандартное отклонение доходности',
    'detail.negativeProbability': 'P(убыток)',
    'detail.ruinedProbability': 'P(разорение)',
    'detail.equity': 'Капитал',
    'detail.totalReturnDistribution': 'Распределение доходности',
    'detail.rMultipleDistribution': 'Распределение R-кратных',
    'detail.historicalRunNote': 'Прогонов 1, потому что исторический бэктест детерминированно проигрывает один фиксированный набор данных один раз. Несколько прогонов нужны для Monte Carlo, где случайные выборки оценивают распределение исходов.',
    'runs.run': 'Прогон',
    'runs.trades': 'Сделки',
    'runs.winRate': 'Доля побед',
    'runs.expectancy': 'Мат. ожидание (выборка)',
    'runs.totalReturn': 'Доходность',
    'runs.maxDrawdown': 'Макс. просадка',
    'runs.profitFactor': 'Профит-фактор',
    'runs.ruined': 'Разорение',
    'charts.equity': 'Капитал',
    'comparison.title': 'Сравнение математического ожидания',
    'comparison.description': 'Перед расчётом deltas значения приводятся к выбранной опорной единице риска.',
    'comparison.counterpart': 'Эксперимент для сравнения',
    'comparison.referenceRisk': 'Опорная доля риска',
    'comparison.compare': 'Сравнить',
    'comparison.noCounterpart': 'Нет экспериментов подходящего типа.',
    'comparison.estimate': 'Оценка',
    'comparison.sourceValue': 'Исходное значение',
    'comparison.referenceValue': 'Опорное значение',
    'comparison.sampleSize': 'Фактически / запланировано сделок',
    'comparison.riskUnitFraction': 'Доля 1R источника',
    'comparison.theoretical': 'Теоретическая',
    'comparison.sample': 'Monte Carlo',
    'comparison.historical': 'Историческая',
    'comparison.delta': 'Delta',
    'comparison.deltaTheoreticalSample': 'Теоретическая − Monte Carlo',
    'comparison.deltaTheoreticalHistorical': 'Теоретическая − историческая',
    'comparison.deltaSampleHistorical': 'Monte Carlo − историческая',
    'comparison.convertedWarning': 'Определения риска различаются. Значения приведены к выбранной общей опорной шкале.',
    'comparison.incompatibleWarning': 'Определения риска нельзя безопасно привести к общей шкале. Deltas недоступны.',
    'type.monte_carlo': 'Monte Carlo',
    'type.historical_backtest': 'Исторический бэктест',
    'status.completed': 'Завершён',
    'status.pending': 'В ожидании',
    'status.failed': 'Ошибка',
    'param.data.source': 'data.source',
    'param.data.path': 'data.path',
    'param.data.symbol': 'data.symbol',
    'param.data.timeframe': 'data.timeframe',
    'param.strategy.type': 'strategy.type',
    'param.strategy.fast_period': 'strategy.fast_period',
    'param.strategy.slow_period': 'strategy.slow_period',
    'param.strategy.stop_loss_pct': 'strategy.stop_loss_pct',
    'param.portfolio.initial_capital': 'portfolio.initial_capital',
    'param.portfolio.risk_per_trade': 'portfolio.risk_per_trade',
    'param.portfolio.commission': 'portfolio.commission',
    'param.portfolio.slippage': 'portfolio.slippage',
    'batches.title': 'Батчи',
    'batches.empty': 'Батчей пока нет.',
    'batches.hypothesis': 'Гипотеза',
    'batches.notes': 'Заметки',
    'batches.experimentCount': 'Экспериментов',
    'batches.createTitle': 'Создать батч',
    'batches.grid': 'Сетка параметров (JSON)',
    'batches.create': 'Создать',
    'batches.missingFieldsError': 'Заполните ID базового эксперимента и гипотезу перед созданием',
    'batches.invalidGridError': 'Сетка параметров должна быть валидным JSON, например {"strategy.fast_period": [8, 10]}',
    'detail.analysis': 'Статистический анализ',
    'detail.expectancyCi': '95% ДИ мат. ожидания',
    'detail.significantVsZero': 'Значимо отличается от нуля',
    'detail.sharpe': 'Sharpe',
    'detail.sortino': 'Sortino',
    'detail.calmar': 'Calmar',
    'detail.exportJson': 'Экспорт JSON',
    'detail.exportMarkdown': 'Экспорт Markdown',
    'oos.title': 'Out-of-Sample',
    'oos.baseExperimentId': 'ID базового эксперимента',
    'oos.trainStart': 'Начало train',
    'oos.trainEnd': 'Конец train',
    'oos.testStart': 'Начало test',
    'oos.testEnd': 'Конец test',
    'oos.run': 'Запустить',
    'oos.train': 'Train',
    'oos.test': 'Test',
    'oos.deltaTrainTest': 'Train − Test',
    'oos.notHistoricalError': 'Out-of-Sample требует эксперимент типа historical_backtest',
    'oos.missingDatesError': 'Заполните начало/конец train и начало/конец test перед запуском',
  },
}

function readStoredLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(localeKey)
    return stored === 'ru' ? 'ru' : 'en'
  } catch {
    return 'en'
  }
}

function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(themeKey)
    return stored === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

const locale = ref<Locale>(readStoredLocale())
const theme = ref<Theme>(readStoredTheme())

function applyPreferences() {
  if (typeof document === 'undefined') return
  document.documentElement.lang = locale.value
  document.documentElement.dataset.theme = theme.value
}

function setLocale(value: Locale) {
  locale.value = value
  try {
    window.localStorage.setItem(localeKey, value)
  } catch {
  }
  applyPreferences()
}

function setTheme(value: Theme) {
  theme.value = value
  try {
    window.localStorage.setItem(themeKey, value)
  } catch {
  }
  applyPreferences()
}

function t(key: string): string {
  return messages[locale.value][key] ?? key
}

applyPreferences()

export function usePreferences() {
  return { locale, theme, setLocale, setTheme, t }
}
