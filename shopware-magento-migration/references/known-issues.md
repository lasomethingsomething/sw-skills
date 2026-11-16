# Known issues & backlog (the "what will bite me" reference)

Curated from the open **Migration Assistant** backlog (label `extension/Migration-Assistant` on
[shopware/shopware](https://github.com/shopware/shopware/issues?q=is%3Aissue+state%3Aopen+label%3Aextension%2FMigration-Assistant)).
The label covers the whole Migration Assistant family (SwagMigrationAssistant, -Connector, -Magento),
so some items mention Shopware 5→6 too — the mechanics apply to the Magento profile as well.

Each entry: **#number — title** · what actually happens · what to do now / status. Use this to set
expectations *before* a migration. Issue numbers link as `shopware/shopware#<number>`.

> **Issue states drift.** This is a point-in-time snapshot. The *symptoms and mechanics* below are
> durable, but before quoting a client that something is "unfixed", confirm the issue is still open
> on the [live tracker](https://github.com/shopware/shopware/issues?q=is%3Aissue+label%3Aextension%2FMigration-Assistant).

**Which layer (see `architecture.md`):** the groups map cleanly onto the two plugins.
*Performance & scale* and *re-runs/connections* are almost all **Assistant framework** concerns (the
queue, `swag_migration_data`, MappingService, the wizard) — they affect every migration, Magento
included. *Data correctness* is mostly the **Magento profile** (its converters and premapping).
Fixing a framework item helps all profiles; fixing a Magento converter helps only Magento
migrations.

(This file deliberately omits pure admin-UX polish and tech-debt/contributing tickets — low value
for debugging a migration. Browse the [live label](https://github.com/shopware/shopware/issues?q=is%3Aissue+label%3Aextension%2FMigration-Assistant)
for those.)

---

## Performance & scale — the migration-killers on big shops

These only show up at scale (hundreds of thousands to millions of rows). Plan for them up front.

- **#10647 — Slow query during the customer import.** A `swag_migration_data` lookup during convert
  (`WHERE entity='customer' AND run_id=… AND convert_failure=0 ORDER BY auto_increment LIMIT 100
  OFFSET …`) examined ~256k rows and ran ~20 minutes. **Check first:** the Assistant has shipped a
  `(entity, run_id, convert_failure)` index since 2019 (`Migration1564053392`), so on current
  versions this is already covered — run `SHOW INDEX FROM swag_migration_data` and `EXPLAIN` before
  acting. `assets/swag_migration_data-index.sql` is only for older installs or to additionally cover
  the `ORDER BY auto_increment` sort.
- **#10645 — Order read performance.** On MySQL 5.7 with 1.1M orders, the order-collecting query
  (many LEFT JOINs + an expensive final sort) ran ~96s and got truncated by nginx's 90s timeout — so
  the migration couldn't complete at all. **Now:** run via the CLI worker (no web timeout), raise
  timeouts, migrate in narrower batches. **Roadmap:** split the query / cursor pagination.
- **#10642 — Optimize read with cursor-based queries.** Root cause of the above: offset-based
  pagination degrades badly as the offset climbs (a well-known MySQL issue). **Roadmap:** switch
  readers to keyset/cursor pagination. Affects all large entity reads, not just orders.
- **#10627 — Refactor MappingService to reduce SQL lookups.** The convert phase does thousands of
  per-record mapping lookups; cutting them speeds converting a lot. Can't trivially move to
  deterministic UUIDv3 without breaking existing users' mapping tables (duplicate-entry risk on
  re-migration). **Roadmap:** batch/group the lookups.
- **#10628 — Caching that lives for one migration run.** Lookup caches are lost between MQ messages,
  so the same data is fetched repeatedly. **Roadmap:** a per-run cache, cleared at run end; profile
  with Blackfire to target the worst methods.
- **#10626 — Combine fetching → converting → writing.** Since the migration no longer depends on
  HTTP requests, the three-phase split (and the giant `swag_migration_data` table) may be
  unnecessary. **Roadmap:** do it all in one MQ message → less storage, save checksums only after a
  record fully migrates, and prevent follow-up errors by knowing what's already done.
- **#10639 — Checksum + `swag_migration_data` reset via MQ.** Checksum reset and clearing
  `swag_migration_data` at run start run synchronously and can time out — some migrations failed to
  even start. **Roadmap:** move both to the message queue.
- **#10635 — End time per migration run.** No end-time recorded. **Roadmap:** add an end-time column
  to `swag_migration_run`, fill on finished/aborted (`MigrationProcessHandler`), show in
  history/log.

## Data correctness — things that land subtly wrong

The dangerous category: the migration "succeeds" but data is wrong. Spot-check these after every
migration.

- **#10649 — Delete write array of mapping per entity on error.** If an entity fails to convert
  (e.g. empty required field) and another entity references it, you get **SQL errors when writing
  the dependent** (e.g. Product → PropertyGroupOption). **Now:** re-run the dependency's selection
  first so its mapping exists. **Fix (branch exists):** drop the failed entity's mapping and have
  dependents check for it and skip. When writing your own converters, *look up the dependency and
  skip the record if absent* (see `extending.md`).
- **#10646 — Default customer group not retained.** The customer group that was the **default** in
  the source isn't re-flagged as the sales channel's default in SW6. **Now:** set the default
  customer group manually post-migration.
- **#10648 — Variant/configurator images not applied to storefront.** Image assignments for variants
  (the "configurator image" setting) aren't carried into SW6's *Variant display in Storefront → Media
  → Characteristics*, forcing large manual post-processing. **Now:** re-assign variant preview images
  manually, or script it from the source assignments.
- **#10650 — Argon2 password encoder.** Password hashes use different encoders across Magento
  versions (MD5/SHA256/Argon2id). **Now:** ensure the profile matches the Magento version so the
  right encoder is registered; otherwise migrated customers can't log in with old passwords.
- **#10607 — Payment-method (data) assignments need manual work.** Even similarly-named payment
  methods must be mapped by hand in premapping. **Now:** budget premapping time; map carefully —
  unmapped methods mis-assign on orders.
- **#10617 — Custom-field prefix not editable.** Migrated custom fields get a fixed, longish prefix
  (collision avoidance) that's permanent and ugly for SaaS projects. **Now:** rename post-migration
  if it matters. **Roadmap:** configurable prefix / later cleanup.
- **#10618 — Import old URLs + 301 redirects.** Old article/category URLs aren't imported as
  redirects, so links/SEO break after restructuring. **Now:** set up 301 redirects yourself.
  **Roadmap:** import source URLs as redirects.
- **#10620 — system_config migration story.** The block list of migrated `system_config` keys keeps
  causing trouble (esp. on cloud, where overriding some keys breaks things). Open questions: block
  list vs allow list, what to do with plugin/app config and instance-related UUIDs. **Now:** review
  what config you actually want migrated; don't assume it's all safe.
- **#14777 — Migration error resolution: future improvements.** Wishlist for the fix-modal, e.g.
  per-error filtering ("only active products") when bulk-fixing. Roadmap/UX.

## Re-runs, selection & connections

- **#10644 — Advanced data selection.** You can only select whole **DataSelections**, not individual
  **DataSets**. So dependencies (customers before orders) get re-fetched on every run even when you
  only want to re-migrate one thing. **Roadmap:** an "advanced data selection" tab to pick
  individual DataSets. **Now:** plan re-run order; expect dependency re-fetch.
- **#10643 — No two active connections at once.** Two simultaneously-active connections can cause
  mapping errors; there's no guard yet. **Now:** finish/archive one connection before activating
  another.

> One UI-behaviour note worth keeping: the migration **changes currency-dependent prices** during
> the run and the wizard doesn't call this out clearly (#10630) — tell clients before they run.

---

### How to use this list when planning a migration

1. **Before quoting a timeline:** read Performance & Data-correctness. The index (#10647) and the
   read-timeout reality (#10645) alone change the plan for any large shop.
2. **Before the run:** `SHOW INDEX FROM swag_migration_data` (the convert index usually already
   ships — see #10647), decide CLI-worker vs foreground, raise timeouts, snapshot the target DB.
3. **After the run:** walk the Data-correctness list as a QA checklist (default customer group,
   variant images, passwords, payment mapping, URLs).
