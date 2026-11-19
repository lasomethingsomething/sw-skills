# Changelog

## 1.1.1
- `SKILL.md`: `project upgrade --dry-run` is no longer called read-only. The skill now says what it writes (`.shopware-cli/upgrade/report.md`, a temporary Composer manifest and lock) and that it runs Composer over the network, and asks before running it.

## 1.1.0
- `SKILL.md`: hard rules, a checklist workflow with one default per step (bundled search; `project upgrade --dry-run`), a plan self-check, and a gotchas list for 6.7.0.0. Privacy detail moved to `references/privacy.md`.
- Removed the bundled issue index and `--include-issues`; issues are searched live as leads.
- Snapshots updated to 6.6.10.32 (adds media upload and path security notes) and 6.7.16.1 (guide unchanged from 6.7.16.0).
- Weekly link and freshness check; version ranges read from `scripts/search_sources.py`.
- Three scenarios on real 6.7 changes (payment handler, Store-API cache decorator, storefront theme overrides).

## 1.0.2
- Paired evaluation helper; evals grouped with the skill.

## 1.0.1
- Tighter review checks.

## 1.0.0
- First tracked behaviour baseline.
