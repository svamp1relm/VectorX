# Contributing to VectorX

Спасибо за вклад в исследовательскую платформу.

## Установка

```bash
uv sync --all-extras
cd web && npm ci
```

Для demo потребуются Docker и Docker Compose. Быстрый запуск описан в README.

## Перед изменениями

- Прочитайте `docs/VECTORX-ARCHITECTURE.md` и `docs/VECTORX-RESEARCH-MODEL.md`.
- Для численных изменений сначала определите backward compatibility и версии алгоритмов.
- Не добавляйте live trading, биржевые ключи или внешнюю инфраструктуру без отдельного решения.
- Не включайте `.env`, credentials, demo volumes и test artifacts в коммит.

## Проверки

```bash
uv run pytest
uv run ruff check .
cd web
npm test
npm run build
```

Browser E2E:

```bash
cd web && npx playwright install chromium && cd ..
./scripts/e2e.sh
```

## Миграции и численная совместимость

- Все изменения БД — только через Alembic.
- Проверяйте upgrade/downgrade и чтение старых данных.
- Изменения execution/metrics требуют regression fixtures и явного version bump.
- Старые эксперименты не переписываются под новые алгоритмы.

## Pull Request

1. Создайте отдельную ветку от актуального `master`.
2. Разделяйте refactor, numerical changes и docs на понятные коммиты.
3. Заполните PR template и перечислите выполненные проверки.
4. Дождитесь зелёного CI.
5. Свяжите PR с issue, если изменение затрагивает исследовательскую семантику.

Сообщения об уязвимостях отправляйте по `SECURITY.md`, а не через публичный issue.
