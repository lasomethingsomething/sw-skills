# Upgrade planner lifecycle

This is an experimental, temporary skill.

- **Owner:** the repository owner (approves every change, receives link and freshness failures).
- **Retire when:** 6.6 reaches end of life, or the 6.8 upgrade approach replaces this planner, whichever comes first.

Version 1.0.0 is the first tracked behavior baseline; it is not a claim of production readiness, comprehensive coverage, GDPR certification, or a fixed support lifetime.

## Change and release

1. Scope each change to the intended 6.6 → 6.7 journey. Keep retrieved third-party text as evidence, not instructions. Review version applicability, source accuracy and privacy before adding material.
2. Add a line to [CHANGELOG.md](../CHANGELOG.md) and bump `metadata.version` in `SKILL.md` whenever instructions, scripts, sources, references, or evaluation scenarios change. Use a quoted SemVer string: patch for compatible corrections, minor for compatible capabilities, major for incompatible behavior or scope. Reset patch to zero for a minor bump and reset minor and patch for a major bump. Versions do not automatically update installed copies; use a tested commit or tag when reproducibility matters.
3. Run the offline validation and unit tests:

   ```bash
   python3 shopware-upgrade-planner/scripts/check_skill.py
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s shopware-upgrade-planner/scripts -p 'test_*.py' -v
   ```

   Validation needs Python 3 and PyYAML; the search script itself uses the Python standard library. For a committed change, pass `--base-ref <base-commit>` to check that changed skill files also bump the version. The CI workflow performs these cheap checks on pull requests before human review.
4. For behavior changes, compare representative tasks with and without the skill, or against the previous version. Use `evals/scenarios.json` as public development cases and keep real holdout cases separate. Review each expectation for one independently assessable outcome; duplicate text is checked automatically, but semantic conflicts and compound expectations need review. Record results and exact tested revisions using `evals/report-template.md`; check that results cover the current changes before release. Do not put shop data, actual prompts containing personal data, credentials or telemetry in evaluation reports. Do not describe a planned or unrun agent evaluation as a pass.
5. Use the upgrade-planner pull-request checklist for a human or opt-in AI-assisted review, then have a Shopware upgrade expert review source accuracy, version applicability, usability and privacy risks before release. This is a review aid, not an automated AI or approval gate. Offline checks cannot establish upgrade coverage, outcome quality or GDPR compliance. The external-link workflow runs weekly and on demand; it also fails when Shopware has tagged a 6.6.10 or 6.7 release newer than the bundled snapshots (add the snapshot, then widen `SOURCE_RANGE`/`TARGET_RANGE` in `scripts/search_sources.py` and the range in `SKILL.md`). redirects, rate limits, login walls and network errors need human interpretation. Verify target-tag guidance separately.

## Maintain and retire

A maintainer should review reports of wrong guidance, version mismatches, deprecated sources, broken external links and updates to bundled source snapshots. Record snapshot refs and limitations in `source-policy.md`, and verify the exact target version before making upgrade claims. When the temporary problem diminishes, review actual usage and need, narrow supported versions, announce retirement and a replacement path, and remove the directory entry only after coordinating with maintainers. Do not assume a calendar date or automatically delete user plans.
