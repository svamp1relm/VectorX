## Summary

<!-- Что изменилось и зачем. -->

## Research compatibility

- [ ] Численные результаты не изменились.
- [ ] Либо numerical changes описаны и версионированы (`experiment_version`/`analysis_version`).

## Verification

- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `npm test`
- [ ] `npm run build`
- [ ] E2E, если изменён пользовательский workflow.
- [ ] Миграции/legacy data, если изменено хранение.

## Documentation and security

- [ ] README/docs обновлены.
- [ ] Новые secrets, paths, network exposure и resource risks рассмотрены.
- [ ] Сгенерированные artifacts не включены.
