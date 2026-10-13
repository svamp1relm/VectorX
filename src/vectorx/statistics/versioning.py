"""`ANALYSIS_VERSION`: version gate for the statistical toolkit (Фаза 19).

Separate from `EXPERIMENT_VERSION` (`vectorx.experiments.versioning`):
bootstrap/CI/risk-adjusted algorithms evolve independently of the core
experiment schema, by design (see the Research Platform Roadmap, Фаза 19,
decision 5). Bump this whenever `vectorx.statistics.confidence`,
`vectorx.statistics.risk_adjusted`, or `vectorx.statistics.significance`'s
algorithm changes in a way that would change previously-computed results.
"""

ANALYSIS_VERSION = 1
