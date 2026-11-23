# sw-skills

Agent skills for Shopware: `shopware-upgrade-planner`, `shopware-upgrade-planner-deluxe` (the planner plus a real-migration field report), `shopware-magento-migration`.

## Review every skill change against these sources

Before committing a new skill or a change to one, check the draft against each source below and fix what it gets wrong. List anything left unfixed, and why, in the commit body or PR.

- [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices): concise `SKILL.md`, gotchas, defaults over menus, checklists and validation loops, scripts for fragile steps.
- [Agent Skills specification](https://agentskills.io/specification): frontmatter, `SKILL.md` under 500 lines, progressive disclosure (say when to load each reference).
- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) and [optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions): scenarios, baselines, trigger descriptions.
- [How we ship Google Agent Skills like products](https://cloud.google.com/blog/topics/developers-practitioners/behind-the-scenes-two-months-later-how-we-ship-google-agent-skills-like-products): versioning, changelog, freshness and link checks, ownership, retirement.

Check facts about tools against their released source (for example a `shopware/shopware-cli` tag), not memory.

## Repo conventions

- Work on `main`; no feature branches.
- Bump `metadata.version` and the skill's `CHANGELOG.md` on every change.
- Run the skill's tests and `scripts/check_skill.py` before committing.
