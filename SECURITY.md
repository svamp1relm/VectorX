# Security Policy

## Supported versions

Активно поддерживается текущий release из `master`. Более старые experiment/analysis versions
остаются читаемыми для воспроизводимости, но security fixes не backportируются автоматически.

## Threat model

VectorX рассчитан на локальный research/demo запуск:

- authentication отсутствует;
- API выполняет вычисления синхронно;
- PostgreSQL demo публикуется только на `127.0.0.1`;
- API CSV paths ограничены `VECTORX_DATA_ROOT`;
- внешняя публикация API/PostgreSQL требует отдельной security-конфигурации.

Не вводите реальные exchange/API keys и не используйте demo credentials вне локальной машины.

## Reporting a vulnerability

Не создавайте публичный issue с нераскрытой уязвимостью. Используйте GitHub Private Vulnerability
Reporting / Security Advisory репозитория, если функция доступна, иначе свяжитесь с владельцем
репозитория через GitHub без включения чувствительных данных в публичные комментарии.

В сообщении укажите:

- affected version/commit;
- preconditions и impact;
- минимальный reproduction scenario;
- возможные credentials/data exposure;
- предлагаемый fix, если есть.

Не помещайте секреты, private keys, production data или полные дампы БД в report.
