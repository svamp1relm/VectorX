# VectorX — план улучшения GitHub-репозитория

**Дата:** 2026-11-19  
**Репозиторий:** https://github.com/svamp1relm/VectorX  
**Актуальная рабочая ветка:** `research-platform-v1` на `adbe0d8`  
**Default branch:** `master` на `c2ed084`

Документ описывает проблемы представления и поставки проекта на GitHub, а не архитектуру кода.
Технические улучшения находятся в `VECTORX-PROJECT-IMPROVEMENT-PLAN.md`.

## 1. Подтверждённое текущее состояние

- Репозиторий публичный.
- `origin/HEAD` указывает на `master`.
- `master` содержит исходный MVP, а актуальная реализация — в `research-platform-v1`.
- GitHub Actions отсутствуют.
- Releases и git tags отсутствуют.
- `licenseInfo: null`.
- Обе ветки возвращают `Branch not protected`.
- Описание репозитория ограничено Monte Carlo и не отражает текущие возможности.
- Topics отсутствуют.
- `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, issue/PR templates отсутствуют.

Главная проблема: человек, открывающий репозиторий, видит старую версию проекта и не имеет
автоматического подтверждения качества текущей.

---

## 2. Приоритет P0 — Актуализировать `master`

### Проблема

Основная ветка не содержит текущий Research Platform, Robustness, remediation-изменения и документацию.

### Задачи

- [ ] Открыть Pull Request `research-platform-v1 → master`.
- [ ] Проверить полный diff и отсутствие локальных untracked файлов в PR.
- [ ] Убедиться, что в PR входят только актуальные исходники, миграции, тесты, docs и lockfile.
- [ ] Запустить 361 backend-тест и 59 frontend-тестов, Ruff, production build и миграции.
- [ ] Влить PR обычным merge commit, чтобы сохранить историю фаз.
- [ ] Проверить, что `master` и `origin/HEAD` содержат актуальный коммит.
- [ ] После успешного выпуска удалить `research-platform-v1` локально и на GitHub либо оставить её
  как long-lived development branch по явному решению.

### Критерий готовности

При открытии репозитория без выбора ветки пользователь видит актуальные README, API, robustness,
миграции и тесты.

---

## 3. Приоритет P0 — Добавить CI

### Проблема

Качество изменений подтверждается только локальными запусками.

### Задачи

- [ ] Создать `.github/workflows/ci.yml` для `master` и Pull Requests.
- [ ] Backend job:
  - checkout;
  - установка Python из зафиксированной версии;
  - установка зависимостей из полного lockfile;
  - `pytest`;
  - `ruff check .`.
- [ ] Frontend job:
  - checkout;
  - установка Node.js;
  - `npm ci`;
  - `npm test`;
  - `npm run build`.
- [ ] Integration job:
  - ephemeral PostgreSQL;
  - Alembic upgrade/downgrade/upgrade;
  - `docker compose config`;
  - repository/query-count tests.
- [ ] Кэшировать Python/Node dependencies без сохранения секретов в логах.
- [ ] Добавить browser E2E job после внедрения Playwright.
- [ ] Сделать CI checks обязательными для `master`.

### Критерий готовности

Каждый PR автоматически получает одинаковые backend/frontend/migration проверки; merge при
неуспешных обязательных checks невозможен.

---

## 4. Приоритет P0 — Лицензия и юридическая ясность

### Проблема

Публичный репозиторий не содержит лицензии, поэтому условия использования и вклада не определены.

### Задачи

- [ ] Выбрать лицензию владельцем проекта, например MIT.
- [ ] Добавить `LICENSE` с корректным copyright holder и годом.
- [ ] Указать лицензию в README и `pyproject.toml`.
- [ ] Проверить отображение лицензии в боковой панели GitHub.

### Критерий готовности

GitHub распознаёт лицензию, а условия использования кода понятны пользователям и contributors.

---

## 5. Приоритет P1 — Релизный процесс

### Проблема

Нет тегов, releases и задокументированной точки стабильной поставки.

### Задачи

- [ ] Обновить package version до `0.2.0`.
- [ ] Добавить `CHANGELOG.md` по Keep a Changelog.
- [ ] Создать git tag `v0.2.0` после merge в `master`.
- [ ] Создать GitHub Release с разделами Added / Changed / Fixed / Security.
- [ ] Описать breaking numerical changes: next-open, gross/net, `experiment_version=2`,
  `analysis_version=2`, миграция `f4b8d2c61a90`.
- [ ] Документировать порядок следующих релизов и hotfixes.
- [ ] Не путать package version и experiment/analysis versions.

### Критерий готовности

Пользователь может скачать стабильную версию, понять изменения и повторить её установку по lockfile.

---

## 6. Приоритет P1 — Метаданные и безопасность GitHub

### 6.1. Описание и topics

**Задачи:**

- [ ] Обновить описание, например: «Research platform for Monte Carlo simulations, historical
  backtesting, OOS validation and robustness analysis».
- [ ] Добавить topics: `backtesting`, `monte-carlo`, `fastapi`, `vue`, `postgresql`, `research`,
  `python`, `typescript`.
- [ ] Проверить ссылки на dashboard/docs в README.

### 6.2. Branch protection

**Задачи:**

- [ ] Для `master` требовать PR перед merge, если появятся collaborators.
- [ ] Требовать успешные CI checks.
- [ ] Запретить force push и удаление `master`.
- [ ] Настроить required reviews по числу maintainers; для личного проекта не создавать искусственный
  обязательный процесс, если он не нужен.
- [ ] Разрешить linear history только если выбран соответствующий merge workflow.

### Критерий готовности

Изменения в `master` проходят предсказуемый процесс без случайной потери истории.

### 6.3. Security policy и dependency monitoring

**Задачи:**

- [ ] Добавить `SECURITY.md`: supported versions, способ приватного сообщения уязвимостей,
  local-only threat model, CSV/API/PostgreSQL boundaries.
- [ ] Включить Dependabot или Renovate для Python, npm и GitHub Actions.
- [ ] Включить доступные GitHub secret scanning/push protection без записи секретов в репозиторий.
- [ ] Не включать auth/live-trading инфраструктуру ради формальности: сначала задокументировать
  локальную модель запуска.

### Критерий готовности

Есть понятный канал для security reports и автоматические уведомления об уязвимых зависимостях.

---

## 7. Приоритет P2 — Документация для пользователей и contributors

### Задачи

- [ ] Добавить `CONTRIBUTING.md`: setup, branch workflow, TDD, migrations, commit checks, PR requirements.
- [ ] Добавить `CHANGELOG.md`.
- [ ] Добавить issue templates: bug, research question, feature request.
- [ ] Добавить PR template: summary, numerical compatibility, tests, migrations, UI, docs, security.
- [ ] Добавить `CODE_OF_CONDUCT.md`, если ожидаются внешние contributors.
- [ ] Добавить ссылки на актуальные architecture/research/API/data docs из главного README.
- [ ] Проверить, что README соответствует содержимому `master`, включая порты, lockfile и security.

### Критерий готовности

Новый contributor может установить проект, выполнить проверки, подготовить PR и понять требования
к совместимости без посторонней помощи.

---

## 8. Рекомендуемый порядок выполнения

1. PR и merge `research-platform-v1 → master`.
2. GitHub Actions backend/frontend/migrations.
3. `LICENSE`.
4. `v0.2.0` tag, GitHub Release и `CHANGELOG.md`.
5. Описание, topics и branch protection.
6. `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates.
7. Полный dependency lock и dependency monitoring.
8. Browser E2E в CI и дальнейшие улучшения из `VECTORX-PROJECT-IMPROVEMENT-PLAN.md`.

## 9. Definition of Done

- Default branch содержит актуальный проект.
- Все обязательные проверки выполняются автоматически на PR.
- Репозиторий имеет лицензию, понятное описание и topics.
- Существует стабильный release с lockfile и release notes.
- Защита `master` соответствует команде и CI.
- Есть инструкции для contributors и security reports.
- Новый пользователь может установить и проверить проект только по GitHub-документации.
