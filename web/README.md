# VectorX — web dashboard

Vue 3 + TypeScript + Vite фронтенд для [VectorX](../README.md). Ничего не считает — только
отображает данные, полученные от `api/main.py` (FastAPI). Вся статистика/метрики/bins считаются
на бэкенде.

## Что внутри

- `src/components/ExperimentsList.vue` → `ExperimentDetail.vue` — список экспериментов, детали
  (параметры, summary, equity-график, гистограммы, таблица runs, Statistical Analysis, экспорт
  JSON/Markdown).
- `src/components/BatchesList.vue` → `BatchDetail.vue` — parameter sweep батчи.
- `src/components/OutOfSampleView.vue` — train/test сравнение.
- `src/components/ExpectancyComparison.vue` — сравнение Monte Carlo vs historical.
- `src/api.ts` — тонкий typed fetch-клиент (зеркало `api/serialization.py`), `src/types.ts` —
  соответствующие типы.
- `src/preferences.ts` — тема (light/dark) и язык (EN/RU), сохраняются в `localStorage`.

## Разработка

```bash
npm ci
cp .env.example .env.local   # при необходимости поправить VITE_API_BASE
npm run dev                  # http://127.0.0.1:5173, требует запущенный API (см. корневой README)
```

## Проверка

```bash
npm test             # vitest
npx vue-tsc --noEmit # проверка типов
npm run build         # production-сборка в dist/
```

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `VITE_API_BASE` | `http://127.0.0.1:8000` | Базовый URL FastAPI-бэкенда |

См. `.env.example`. Vite подхватывает `.env.local` (игнорируется git).
