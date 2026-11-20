# VectorX — accessibility checklist

Component и Playwright тесты покрывают базовые механизмы. Этот список предназначен для ручной проверки
перед релизом; его нельзя считать выполненным только по успешной production-сборке.

## Keyboard

- [x] Experiment row активируется Enter/Space (component test).
- [x] Главная навигация активируется клавиатурой (Playwright).
- [x] Batch rows имеют focus/Enter/Space handlers.
- [ ] Полный пользовательский workflow пройден только клавиатурой вручную.

## Names и announcements

- [x] Основные view buttons имеют `aria-pressed`.
- [x] Loading/error состояния используют `role=status`/`role=alert` в основных workflows.
- [x] Canvas имеет accessible name.
- [ ] Проведена проверка реальным screen reader.

## Charts и данные

- [x] Equity/histogram имеют раскрываемую табличную альтернативу.
- [x] Chart.js ticks/legend используют theme-aware text color.
- [ ] Контраст проверен инструментом в light/dark темах на реальном рендере.

## Responsive

- [x] Навигация переносится, таблицы имеют section overflow, definition lists становятся одноколоночными.
- [ ] Проверены 320px, 720px и desktop в EN и RU на реальных длинных значениях.
- [ ] Нет недоступного содержимого при горизонтальной прокрутке.

## Async correctness

- [x] Required request failures видимы и не заменяются нулевыми метриками (component + Playwright).
- [x] Comparison/OOS/Robustness защищены от stale/repeated запусков.
- [x] Null/empty значения отображаются как `—` или явное empty state.

## Как выполнять ручную проверку

1. `./scripts/demo-up.sh && ./scripts/seed_demo.sh`.
2. Открыть `http://127.0.0.1:5173`.
3. Пройти Experiments, Batches, OOS и Robustness клавиатурой.
4. Переключить EN/RU и Light/Dark.
5. Повторить основные views на ширинах 320/720/1280px.
6. Заполнить чек-лист результатами и связать его с релизом.
