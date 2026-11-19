# Source policy

The snapshot search is a starting point, not an authoritative or exhaustive change register. Shopware's root upgrade guides are reproduced byte-for-byte under `sources/` (no added table of contents; `scripts/search_sources.py` is their index) from the MIT-licensed [shopware/shopware repository](https://github.com/shopware/shopware). The repository license is in `sources/LICENSE`.

| Snapshot | Source | Intended use |
| --- | --- | --- |
| 6.6.10.0 | [UPGRADE-6.6.md](https://github.com/shopware/shopware/blob/v6.6.10.0/UPGRADE-6.6.md) | Exact source snapshot for the first example |
| 6.6.10.32 | [UPGRADE-6.6.md](https://github.com/shopware/shopware/blob/v6.6.10.32/UPGRADE-6.6.md) | Broader 6.6 announcements, including later edits |
| 6.7.0.0 | [UPGRADE-6.7.md](https://github.com/shopware/shopware/blob/v6.7.0.0/UPGRADE-6.7.md) | Exact target snapshot for the first example |
| 6.7.16.1 | [UPGRADE-6.7.md](https://github.com/shopware/shopware/blob/v6.7.16.1/UPGRADE-6.7.md) | Exact 6.7.16.1 snapshot and candidate discovery for intermediate targets |

Snapshot retrieval is not a substitute for reviewing the exact source and target tags. For intermediate versions, the search uses the nearest later bundled snapshot and filters release headings; later edits may still change older sections. Check the exact target-tag file when available. Search 6.6 records for announcements relevant to the target even if the user has already installed the source version, but do not present all past 6.6 changes as new.

Use release notes, official migration guides and merged change evidence to clarify version and status. Issue reports are individual accounts, not automatically confirmed bugs. Check issue status, comments, linked PRs, fix release and project relevance before including one. A closed issue does not establish that a fix shipped in a particular version. Do not treat 6.8/6.9 announcements, later 6.7 releases, or planned/withdrawn work as breaking changes in an earlier target.

GitHub issues are leads, found with generic search terms against the live repositories (`shopware/shopware`, `shopware/shopware-cli`). Public issues may contain personal data; don't copy reporters, comments, logs or screenshots into plans.

Useful entry points:

- [Shopware 6.7.0.0 release](https://github.com/shopware/shopware/releases/tag/v6.7.0.0)
- [Version upgrades and migrations](https://developer.shopware.com/docs/guides/upgrades-migrations/)
- [Administration Vite migration](https://developer.shopware.com/docs/guides/upgrades-migrations/administration/vite.html)
- [Shopware 6.7 update guide](https://docs.shopware.com/en/shopware-6-en/update-guides/update-guide-shopware-67)
- [CLI upgrade command](https://github.com/shopware/shopware-cli/blob/0.20.0/cmd/project/project_upgrade.go)
- [Shopware language server](https://github.com/shopware/shopware-lsp)

Current documentation may cover a newer version than the user's target. Prefer version-specific sources and say when their availability or completeness is uncertain.

Other selected background, which may describe later versions or pre-release plans:

- [Introducing Shopware 6.7](https://www.shopware.com/en/news/introducing-shopware-6-7/)
- [6.7 release candidate 5](https://www.shopware.com/en/news/shopware-6-7-release-candidate-5/)
- [When and why to upgrade](https://www.shopware.com/en/news/major-6-7-when-and-why-to-upgrade/)
- [6.7 major release overview](https://www.shopware.com/nl/news/new-major-release-shopware-6-7/)
- [Project upgrade workflow](https://www.shopware.com/en/news/introducing-projct-upgrade-safer-local-upgrade-workflow-shopware-cli/)
- [Deprecation metadata background](https://www.shopware.com/en/news/when-deprecated-cries-wulf-making-shopware-major-upgrades-easier/)
- [Caching system background](https://www.shopware.com/en/news/new-caching-system/)
