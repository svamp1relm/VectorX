# VectorX — исследовательская модель и интерпретация результатов

## R и капитал

`R` — единица риска, не процент доходности. Для Monte Carlo единица задаётся моделью; для historical:

```text
r_multiple = (exit_price - entry_price) / (entry_price * stop_loss_pct)
```

`stop_loss_pct` нормирует риск, но **не является исполняемым stop-loss**. Внутрисвечной стоп не
моделируется, поэтому убыток может быть меньше −1R.

Портфель рискует долей текущего equity:

```text
risk_amount = equity_before_trade * risk_per_trade
net_r = gross_r - commission_r - slippage_r
pnl_money = risk_amount * net_r
```

Поддерживается одна последовательная long/flat позиция; short и pyramiding отсутствуют.

## Historical execution

1. Стратегия получает свечу `t` и формирует сигнал по доступным на её close данным.
2. BUY/SELL исполняется по open следующей свечи `t+1`.
3. Сигнал последней свечи не исполняется.
4. Уже открытая позиция в конце набора принудительно закрывается по close последней свечи.

Это исключает вход по цене, которая ещё не была доступна в момент сигнала.

## Gross и net метрики

`Trade.r_multiple` остаётся gross R. После портфельного sizing сохраняется `net_r_multiple`.

- Поля без суффикса описывают gross статистику для совместимости и model comparisons.
- Поля `*_net` и net analysis учитывают комиссии/slippage.
- Expectancy comparisons используют `cost_basis` и не смешивают gross/net молча.
- Sharpe/Sortino — unannualized per-trade ratios, не годовые time-series показатели.
- Calmar для multi-run показывается per run; mean return одного run не делится на drawdown другого.

## Empty historical runs

Отсутствие сигналов — валидный результат:

- `trades=0`;
- `total_return=0`;
- `max_drawdown=0`;
- equity остаётся равным initial capital;
- trade-derived expectancy/win rate/profit factor/Sharpe недоступны (`null`, в UI — `—`).

Пустой OOS test получает `insufficient_trades`, а не числовую delta.

## Monte Carlo и случайность

Для run `i` используется `SeedSequence([experiment_seed, i])`. Одинаковые spec, seed и source version
воспроизводят результат. Historical детерминирован и обычно имеет один run.

Random Entry — стохастическая historical benchmark-стратегия. Один seeded run представляет одну
реализацию, а не полное null distribution; выводы о «превосходстве над случайностью» требуют
дополнительных реализаций/исследовательского дизайна.

## OOS и warm-up

Train/test диапазоны обязательно timezone-aware и не пересекаются. До scored start стратегия получает
pre-range candles только для indicator warm-up. Сделки и PnL warm-up не учитываются; позиционное
состояние сбрасывается в flat на scored start.

OOS работает на in-memory срезах без временных CSV. Ответ содержит:

- original base spec;
- requested time ranges и warmup start;
- source data hash и hash фактического среза;
- `executable_spec=false`, поскольку spec без range metadata не является полным OOS-воспроизведением.

## Walk-forward

Walk-forward — последовательность независимых OOS запусков с фиксированными train/test окнами и шагом.
Генерация ограничена 100 полными окнами. Платформа не выбирает «лучший» набор параметров автоматически.

## Bootstrap

Обычный bootstrap ресэмплирует отдельные значения и предполагает независимость наблюдений.

Moving-block bootstrap сохраняет последовательные блоки. Для нескольких Monte Carlo runs блоки
создаются независимо внутри каждого run; cross-run зависимость не выдумывается. Run means объединяются
с весами фактических длин. Доступны gross/net cost basis.

Для исторических серий с сильной зависимостью binary «significant vs zero» по i.i.d. bootstrap следует
интерпретировать с учётом этого предположения и сопоставлять с block-bootstrap robustness.

## Resource limits

Платформа локальная и синхронная. Существуют preflight/aggregate лимиты на число комбинаций, operations,
runs, CSV candles, walk-forward windows и bootstrap work. Эти лимиты защищают исследовательский процесс,
но не превращают API в distributed/job-queue систему.
