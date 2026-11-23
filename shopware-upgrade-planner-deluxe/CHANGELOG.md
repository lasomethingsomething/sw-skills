# Changelog

## 1.0.0
- Forked from `shopware-upgrade-planner` 1.1.2 (same workflow, sources, scripts and privacy rules).
- `references/field-report.md`: lessons from a public retrospective of one real 6.6 → 6.7 migration, split into guide-confirmed changes and findings to check.
- `SKILL.md`: the plan adds a dependency report, separate commits for mechanical and semantic changes, an upgrade CI gate (production asset builds, `project validate`, migrated-database run) and smoke tests on changed surfaces; two self-check items; gotchas for `getEntityName()`, the `ScheduledTaskHandler` logger, `setTwig` and `technicalName`.
- Two scenarios: scheduled-task handler constructor, upgrade CI gate.
