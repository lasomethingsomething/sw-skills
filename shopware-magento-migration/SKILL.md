---
name: shopware-magento-migration
description: >-
  Migrate Magento 2.x or 1.9 to Shopware 6 using SwagMigrationAssistant and SwagMigrationMagento.
  Use when installing or configuring the migration, troubleshooting missing or incorrect data,
  slow or timed-out queries, mappings, media, payment methods, passwords or URLs, or extending
  Magento migration converters, readers and datasets. Triggers include "Magento to Shopware",
  "SwagMigrationMagento", "Migration Assistant", "migration converter/reader", "migration is
  slow", "migrated data missing" and "swag_migration_data".
---

# Migrating a Magento shop to Shopware 6

This skill helps a developer or agency move a **Magento 2.x (or 1.9) shop to Shopware 6** — running
the migration, troubleshooting it at scale, and extending it when Magento has data the profile
doesn't map yet. Keep the audience in mind: the reader is usually mid-migration on a real client
shop, or about to be. Favour "here's the gotcha and the workaround" over exhaustive theory.

> **Verified against SwagMigrationAssistant 18.0 / SwagMigrationMagento 13.0 (Shopware 6.7).**
> File paths, class names, and issue states below reflect those versions. Before relying on a
> specific path or an "open issue" claim, confirm against the installed plugins
> (`composer show swag/migration-assistant swag/migration-magento`) and the live tracker.

## First, the thing that confuses everyone: it's two plugins

A Magento→Shopware migration is not one tool. It's a **framework + a profile**, and you must know
which is which to install, run, or debug anything:

| | Plugin | Repo | What it owns |
|---|---|---|---|
| **Framework / runtime** | **SwagMigrationAssistant** (free base plugin) | [shopware/SwagMigrationAssistant](https://github.com/shopware/SwagMigrationAssistant) | The whole engine: the run **state machine** + message queue, the `swag_migration_*` database tables, the **MappingService**, **premapping**, **error resolution**, media handling, indexing, the **admin wizard UI**, and the **base PHP classes** every profile extends (`Converter`, `DataSet`, `DataSelection`, `ReaderInterface`, `GatewayInterface`, `MappingService`, premapping/writer bases). Ships Shopware 5→6 and 6→6 profiles in-box. |
| **Magento source profile** | **SwagMigrationMagento** | [shopware/SwagMigrationMagento](https://github.com/shopware/SwagMigrationMagento) | A *profile that plugs into the Assistant* to add **Magento** as a source: the Magento profiles (1.9, 2.0–2.4), the **local-DB gateway**, the **Readers** (SQL against the Magento DB), the **Converters** (Magento row → Shopware payload), **DataSets/DataSelections**, Magento **premapping**, the **password encoders**, and the credential form. Requires the Assistant (`composer.json`: `swag/migration-assistant`). |

The profile plugs in purely through **DI tags** the Assistant scans for
(`shopware.migration.profile`, `.gateway`, `.reader`, `.converter`, `.data_set`, `.data_selection`,
`.pre_mapping_reader`, `.writer`, `.media_file_processor`). Everything Magento-specific is "just"
tagged services the framework discovers and drives.

**Why this matters constantly:** when something breaks, the *first* question is always *which layer*.
A stuck run, a timeout, the wizard, the mapping table, error resolution → **Assistant**. Magento data
read wrong, a field mapped wrong, a Magento-specific crash → **Magento profile**. The rest of this
skill keeps pointing back to this split.

> Magento connects via the **local gateway only** — direct read access to the **Magento MySQL
> database**. There is no Magento API gateway, and the "Migration Connector" plugin you'll see in the
> docs is **only for Shopware-5 sources**, not Magento. Ignore it for a Magento migration.

## The mental model (read this before anything else)

The Assistant runs every migration as a **state machine** advanced by the **message queue**
(`src/Migration/Run/MigrationStep.php`: `fetching → writing → media-processing → indexing`, plus
`error-resolution`, `cleanup`, `aborting`, `finished`). Conceptually the data moves in three stages,
and the Magento profile supplies the Magento-specific piece of each:

```
  Magento DB ──read──▶ swag_migration_data ──convert──▶ swag_migration_data ──write──▶ Shopware 6
   (source)    Reader     (raw payload)       Converter    (converted payload)  Writer    (entities)
   [Magento     [Magento]                      [Magento]                        [Assistant + DAL]
    MySQL]                                          │
                                                    └── resolves ids via ──▶ swag_migration_mapping
                                                        (Magento id ↔ Shopware UUID)  [Assistant]
```

- **Read** (Magento profile's Readers) pull raw rows out of the Magento DB and stage them in
  `swag_migration_data`.
- **Convert** (Magento profile's Converters, extending the Assistant's `Converter`) reshape each
  Magento record into Shopware's schema, flattening Magento's **EAV** tables and resolving every old
  id to a Shopware UUID via the Assistant's **MappingService**. Conversion writes payloads back to
  `swag_migration_data`; it never writes shop entities.
- **Write** (Assistant) persists real Shopware entities via the DAL, then media + indexing run.
- **Mapping** (`swag_migration_mapping`, Assistant) is the spine: it remembers Magento customer
  group `1` → Shopware UUID `abc…`, which makes cross-entity references and incremental re-runs work.
- **Premapping** (Assistant engine + Magento's premapping readers) happens *before* the run: values
  that can't be auto-resolved (salutations, payment/shipping methods, order states, tax classes) are
  mapped by the user once.
- **Checksums** (Assistant) let re-runs skip unchanged records.

Locating the stage is 80% of any fix: *missing/garbled field* → Converter (Magento); *slow/timing
out* → Reader SQL (Magento) or MappingService lookups (Assistant); *wrong cross-reference* →
mapping/premapping; *crash on write* → a dependency that failed to convert.

## The Magento profile is versioned and layered

The profile supports Magento **1.9** and **2.0–2.4**, in a deliberate **three-tier** layout you must
understand before editing:

- **`src/Profile/Magento/`** — the **all-versions base**, where the real converter bodies and
  abstract readers live for *every* entity (each `extends MagentoConverter`), plus data sets, data
  selections, premapping, the `MagentoMappingService`, and media. Examples: `Converter/ProductConverter`,
  `CustomerConverter`, `CustomerGroupConverter`.
- **`src/Profile/Magento2/`** — an **optional intermediate** layer for entities whose behaviour has
  a 2.x-shared delta over 1.9. It subclasses the all-versions base (e.g. `Magento2ProductConverter
  extends ProductConverter`) and only exists for a few entities (Product, Customer, Order,
  SalesChannel today); most entities skip this tier.
- **`src/Profile/Magento20/` … `Magento24/`** (and `Magento19/`) — thin **version-specific**
  subclasses (a converter is often just `supports()`; a reader is often just the version's SQL),
  subclassing whichever base above is closest, wired via `parent="…"` in the DI XML.

So adding an entity = put the base logic in **`Profile/Magento/`** (it serves every version); add a
`Profile/Magento2/` subclass **only** if some behaviour must differ across all of 2.x vs 1.9; then a
thin concrete per version. (The Assistant itself uses the same base-vs-version pattern for its
Shopware 5.4–5.7 profiles.) → `references/extending.md`.

## Running a Magento migration: lead with the scale gotchas

The happy path (install **both** plugins, create a Magento local-gateway connection with the Magento
DB credentials, do the premapping, select data, run the queue) is in
`references/running-a-migration.md`. But the value here is the **stuff that bites real shops**, all
from the live backlog:

- **Reads get pathologically slow at high offsets.** Order/customer reads use offset pagination,
  which MySQL degrades on badly as the offset climbs (1.1M orders → 96s queries → killed by a 90s
  nginx timeout). Know this *before* a big migration. (#10645, #10642)
- **Slow `swag_migration_data` lookups during convert.** A composite index on
  `(entity, run_id, convert_failure)` keeps the per-page lookup fast — but the Assistant has shipped
  it since 2019, so on any current version it's *already there*. Run `SHOW INDEX FROM
  swag_migration_data` before assuming it's missing; `assets/swag_migration_data-index.sql` covers
  only the older-version and extra-sort-coverage cases. (#10647)
- **One un-convertible record can cascade into SQL write errors** for entities that depend on it.
  (#10649)
- **Data that silently lands wrong:** default customer group not re-flagged as default (#10646);
  variant/configurator images not applied to the storefront (#10648); payment/shipping methods need
  heavy manual premapping (#10607); custom-field prefixes are fixed and ugly (#10617); old URLs get
  no 301 redirects (#10618); passwords need the right encoder for the Magento version (#10650).

`references/known-issues.md` is the curated catalogue — grouped by symptom, each with the issue
number, what actually happens, the workaround/status, **and whether it's a framework or Magento-
profile concern.** Read it before quoting a client a timeline.

## Extending: a fixed set of Magento-profile building blocks

To migrate a Magento entity the profile doesn't handle yet, you work **in the Magento plugin**,
extending the **Assistant's** base classes:

1. A **Reader** (SQL to pull it from Magento) — abstract in `Profile/Magento/Gateway/Local/Reader/`,
   concrete per version; implements the Assistant's `ReaderInterface`.
2. A **Converter** (Magento row → Shopware payload, ids resolved via MappingService) — abstract in
   `Profile/Magento/Converter/` extending the Assistant's `Converter`, concrete per version.
3. A **DataSet** (declares the entity) in `Profile/Magento/DataSelection/DataSet/`, extending the
   Assistant's `DataSet`.
4. Attach the DataSet to a **DataSelection** (the UI grouping the user ticks).
5. **Register** everything in the Magento plugin's DI XML (`src/DependencyInjection/magento*.xml`)
   with the framework's tags — once per supported Magento version.

Full walkthrough, the converter-test pattern (using the Assistant's `DummyMappingService`), and
copy-paste skeletons: `references/extending.md`, `assets/new-entity-checklist.md`, `assets/skeletons/`.

## A few habits that save migrations

- **Always name the layer first.** Runtime/queue/wizard/mapping symptom → Assistant; Magento data/
  field/SQL symptom → Magento profile. It changes where you look and what you read.
- **Test converters with fixtures, not a live DB.** Seed a `DummyMappingService` with the mappings a
  converter looks up + a `_fixtures/<entity>_data.php` sample of real Magento rows. → `references/extending.md`
- **Profile SQL on the real dataset.** The performance cliffs only appear at scale; a 200-product
  demo shop will never reveal them.
- **Match the Magento version to the profile.** 2.0–2.4 schemas are close but not identical (notably
  password encoders — `Md5`/`Sha256`/`Argon2Id13`); the wrong profile silently mis-reads.
- **Never assume a re-run is free.** Checksums and mapping make re-runs incremental, but a botched
  reset of either can corrupt a migration. → `references/known-issues.md`.
- **Mind the language.** Real migration issues and shop data are often German; Magento source field
  names are its English EAV attribute codes.

## Reference files

- `references/architecture.md` — the two layers in full: the **Assistant runtime** (run state
  machine, message queue, `swag_migration_*` tables, MappingService, premapping, error resolution,
  media, the base classes, the DI tag registries) and the **Magento profile** (profiles, local
  gateway, readers, converters, data sets, premapping, password encoders) — with concrete file paths
  in *both* repos and how they connect.
- `references/running-a-migration.md` — install both plugins, create the Magento connection, premap,
  select data, run via the queue, and a symptom→layer→action troubleshooting table.
- `references/extending.md` — add a Magento entity end to end (Reader + Converter + DataSet +
  DataSelection + DI), fix a converter, and the converter-test pattern.
- `references/known-issues.md` — the curated Migration Assistant backlog, grouped by symptom and
  tagged framework vs Magento-profile.

## Assets (in `assets/`)

- `swag_migration_data-index.sql` — diagnostic + composite index for slow convert lookups (#10647);
  note the base index already ships on current versions — `SHOW INDEX` first.
- `new-entity-checklist.md` — a copy-paste checklist for adding a Magento entity.
- `skeletons/` — minimal `Reader`, `Converter`, and `DataSet` PHP templates (Magento-profile classes
  extending the Assistant's bases), ready to adapt.
