# Architecture: how a Magento → Shopware 6 migration works

A Magento migration is built from **two plugins**. This reference is split the same way:

- **Part A — the Assistant runtime** ([shopware/SwagMigrationAssistant](https://github.com/shopware/SwagMigrationAssistant)):
  the framework that runs *every* migration. Paths below prefixed `assistant: src/…`.
- **Part B — the Magento profile** ([shopware/SwagMigrationMagento](https://github.com/shopware/SwagMigrationMagento)):
  the plugin that adds Magento as a source. Paths prefixed `magento: src/…`.

The Magento profile depends on the Assistant (`magento: composer.json` → `swag/migration-assistant`)
and plugs in entirely through DI tags (Part C). Keep asking *which layer* — it's the fastest way to
the right file.

---

## Part A — The Assistant runtime (framework)

### The run is a state machine driven by the message queue
A migration run is a row in `swag_migration_run` whose `step` advances through
`assistant: src/Migration/Run/MigrationStep.php`:

```php
enum MigrationStep: string {
    case IDLE = 'idle';
    case FETCHING = 'fetching';
    case ERROR_RESOLUTION = 'error-resolution';
    case WRITING = 'writing';
    case MEDIA_PROCESSING = 'media-processing';
    case CLEANUP = 'cleanup';
    case INDEXING = 'indexing';
    case FINISHED = 'finished';
    case ABORTED = 'aborted';
    // …WAITING_FOR_APPROVE, ABORTING
}
```

Each step is handled by a **processor** in
`assistant: src/Migration/MessageQueue/Handler/Processor/` — `FetchingProcessor`, `WritingProcessor`
(does the convert + write), `MediaProcessingProcessor`, `IndexingProcessor`, plus
`AbortingProcessor`/`CleanUpProcessor`. The queue handler
(`assistant: src/Migration/MessageQueue/Handler/MigrationProcessHandler.php`) looks up the processor
for the current step via `MigrationProcessorRegistry` and runs it, then the run advances. Because
it's queue-driven, a large migration survives request timeouts and can pause/resume — **but only if
workers are consuming the queue** (see `running-a-migration.md`). Orchestration entry points:
`assistant: src/Migration/Run/RunService.php`.

### The persistent tables (all owned by the Assistant)
- **`swag_migration_run`** — one row per run: step, progress, totals, environment info.
- **`swag_migration_data`** — staging: the raw fetched payload, then the converted payload, per
  record per run. Large; source of several performance gotchas (`known-issues.md`).
- **`swag_migration_mapping`** — the id translation table `(connectionId, entity, oldIdentifier) →
  Shopware UUID`. The spine of cross-entity references and incremental re-runs.
- **`swag_migration_connection`** — connection + credentials (for Magento: the DB host/user/etc.).
- **`swag_migration_media_file`** — media metadata (source URL, target UUID, status).
- **`swag_migration_logging`** — per-record logs (errors/warnings).
- **`swag_migration_general_setting`**, **`swag_migration_fix`** — settings; error-resolution fixes.

### Base classes every profile extends
These live in the Assistant; the Magento profile subclasses them:
- **`ProfileInterface`** (`assistant: src/Migration/Profile/ProfileInterface.php`) — identifies a
  source system + version.
- **`GatewayInterface`** (`assistant: src/Migration/Gateway/GatewayInterface.php`) — `getName()`,
  `supports(ProfileInterface)`, `read(MigrationContext)`, `readEnvironmentInformation()`,
  `readTotals()`.
- **`Converter`** (`assistant: src/Migration/Converter/Converter.php`, `abstract … implements
  ConverterInterface`) — provides `generateChecksum()`, `convertValue()`, mapping helpers; subclasses
  implement `supports()`, `getSourceIdentifier()`, `convert()`.
- **`DataSet`** (`assistant: src/Migration/DataSelection/DataSet/DataSet.php`) and
  **`DataSelectionInterface`**; entity keys in
  `assistant: src/Migration/DataSelection/DefaultEntities.php`.
- **`ReaderInterface`** / `AbstractReader`, **`MappingServiceInterface`**
  (`assistant: src/Migration/Mapping/`), **premapping** (`assistant: src/Migration/Premapping/`),
  **writers** (`assistant: src/Migration/Writer/`), **media processors**
  (`assistant: src/Migration/Media/`).
- **`MigrationContext`** (`assistant: src/Migration/MigrationContext.php`) — carries the connection,
  profile, gateway, current data set, offset/limit; created by `MigrationContextFactory`.

### Framework features you get for free (don't reimplement in the profile)
- **MappingService** — id translation + lookups; the single biggest convert-phase performance lever
  (backlog #10627/#10628). The Magento profile *extends* it as `MagentoMappingService` (Part B).
- **Premapping engine** — collects unresolvable values and persists the user's choices; the profile
  only supplies the readers that say *which* values need mapping.
- **Error resolution** (`assistant: src/Migration/ErrorResolution/`) — the "fix-it" modal for failed
  records, stored in `swag_migration_fix`; surfaced via `ErrorResolutionController`. Backlog #14777,
  #10649 live here.
- **Media** handling, **indexing**, **history** (`assistant: src/Migration/History/`), **logging**,
  **validation**, and the **admin wizard UI** (Part D).
- **DataProvider** (`assistant: src/DataProvider/`) — only relevant to Shopware 6→6 migrations (it
  exposes a Shopware 6 shop as a source). **Not used by Magento migrations.**

---

## Part B — The Magento profile (what plugs in)

### Profile — *which source + version*
`magento: src/Profile/Magento2/Profile/Magento2Profile.php` (abstract), concrete per version
(`Magento20Profile … Magento24Profile`, plus `Magento19`). Mostly identity metadata:

```php
abstract class Magento2Profile implements MagentoProfileInterface {
    public const SOURCE_SYSTEM_NAME = 'Magento';
    public const PROFILE_NAME = 'magento';
    public const SOURCE_SYSTEM_VERSION = 'X';   // overridden per version
    public function getName(): string { return static::PROFILE_NAME; }
}
```
Every Reader/Converter/DataSet checks `$migrationContext->getProfile() instanceof <Profile>` in
`supports()`. Tag: `shopware.migration.profile`.

### Gateway — *local DB only*
`magento: src/Profile/Magento2/Gateway/Local/Magento2LocalGateway.php` (`… implements
MagentoGatewayInterface`). Connects **directly to the Magento MySQL database** (host/port/user/
password/dbName, optional table prefix) via `magento: src/Profile/Magento/Gateway/Connection/
ConnectionFactory.php`. **There is no API gateway** (the directory only has `Connection/` + `Local/`)
and **no Migration Connector** (that's a Shopware-5-source thing). `read()` delegates to the
registered Reader:

```php
public function read(MigrationContextInterface $migrationContext): array {
    return $this->readerRegistry->getReader($migrationContext)->read($migrationContext);
}
```
Also `readEnvironment()` (via `EnvironmentReader` — validates connection, table prefix, currencies).
Tag: `shopware.migration.gateway`.

### Reader — *the SQL that pulls Magento rows*
Abstract bases in `magento: src/Profile/Magento/Gateway/Local/Reader/` (`AbstractReader`,
`CategoryReader`, `CustomerReader`, `ProductReader`, …); concrete SQL per version in
`magento: src/Profile/Magento2{0..4}/Gateway/Local/Reader/`. Shape: `read(MigrationContext, $params)`
returns row arrays; `readTotal()` returns a count for the progress bar. This is where Magento's
**EAV** model is queried (attributes spread across `*_entity_{varchar,int,decimal}` joined by
attribute id) and where the **performance cliffs** live — offset pagination + heavy joins (#10645,
#10642). Tag: `shopware.migration.reader`, wired to the base via `parent="…"`.

### Converter — *Magento row → Shopware payload*
Real logic lives in an abstract base in `magento: src/Profile/Magento/Converter/` (e.g.
`ProductConverter`, `CustomerConverter`) — this is the all-versions base for *every* entity. A few
entities additionally have an intermediate `magento: src/Profile/Magento2/Converter/` subclass
(`Magento2ProductConverter extends ProductConverter`, `Magento2CustomerConverter`, …) that adds the
behaviour shared across 2.x but different from 1.9. Concrete `supports()`-only subclasses live in
`magento: src/Profile/Magento2{0..4}/Converter/`. All extend `MagentoConverter`
(`magento: src/Profile/Magento/Converter/MagentoConverter.php`), which extends the Assistant's
`Converter`.

The annotated canonical `convert()` body is kept single-source in
`assets/skeletons/MyEntityConverter.php` (so it can't drift); `CustomerGroupConverter.php` is a good
real, minimal example to read alongside it. Conventions it encodes: every old id → UUID via
`getOrCreateMapping`/`getMapping`; **look up foreign references and skip the record if absent** (the
#10649 cascade); return leftover data as the 2nd `ConvertStruct` arg; `convertValue()` with a
`TYPE_*` constant for casting. The per-version subclass is usually just a `supports()` binding the
logic to one profile + data set. Tag: `shopware.migration.converter`.

### DataSet & DataSelection
DataSets (`magento: src/Profile/Magento/DataSelection/DataSet/`, e.g. `ProductDataSet`,
`CustomerDataSet`, `OrderDataSet`, `MediaDataSet`) declare each migratable entity:

```php
class CustomerGroupDataSet extends DataSet {
    public static function getEntity(): string { return DefaultEntities::CUSTOMER_GROUP; }
    public function supports(MigrationContextInterface $m): bool { return $m->getProfile() instanceof MagentoProfileInterface; }
}
```
DataSelections (`magento: src/Profile/Magento/DataSelection/`: `BasicSettingsDataSelection`,
`ProductDataSelection`, `CustomerAndOrderDataSelection`, `MediaDataSelection`, …) bundle the DataSets
that migrate together **and declare their order** (dependencies first). You can't cherry-pick a
single DataSet today — only whole selections (the motivation for #10644). Tags:
`shopware.migration.data_set`, `shopware.migration.data_selection`.

### MappingService, Premapping, Media, Password encoders
- **`MagentoMappingService`** (`magento: src/Migration/Mapping/MagentoMappingService.php`,
  `extends MappingService implements MagentoMappingServiceInterface`) — adds Magento helpers like
  `getUuidList(...)` on top of the Assistant's mapping.
- **Premapping** (`magento: src/Profile/Magento/Premapping/`) — readers for Magento values that need
  manual mapping (salutations, payment/shipping methods, order/delivery states, tax classes). Tag:
  `shopware.migration.pre_mapping_reader`. Heavy manual effort here = UX complaints #10607, #10630.
- **Media** (`magento: src/Profile/Magento/Media/`) — fetches files from the Magento media dir/URL;
  tag `shopware.migration.media_file_processor`.
- **Password encoders** (`magento: src/Profile/Magento2/PasswordEncoder/`:
  `Magento2Md5Encoder`, `Magento2Sha256Encoder`, `Magento2Argon2Id13Encoder`;
  `magento: src/Profile/Magento19/PasswordEncoder/MagentoEncoder.php`) — let migrated customers keep
  their old passwords. The right encoder depends on the Magento version/profile (#10650).

### The version layering, concretely
The base logic for every entity lives in **`Profile/Magento/`**; `Profile/Magento2/` is an optional
intermediate that only some entities use:
- **`Profile/Magento/`** — all-versions base, real logic (e.g. `Converter/CustomerGroupConverter`,
  `Converter/ProductConverter`).
- **`Profile/Magento2/`** — optional intermediate for the 2.x-vs-1.9 delta; subclasses the
  all-versions base (`Magento2ProductConverter extends ProductConverter`). Only Product, Customer,
  Order, SalesChannel have one today.
- **`Profile/Magento20…24/`** (and `Magento19/`) — version-specific concretes, often just `supports()`.

**CustomerGroup** (no `Magento2` layer — `Magento/` → version directly):
| Layer | File |
|---|---|
| Base converter (logic) | `magento: src/Profile/Magento/Converter/CustomerGroupConverter.php` |
| Concrete converter | `magento: src/Profile/Magento20/Converter/Magento20CustomerGroupConverter.php` (just `supports()`) |
| Concrete reader | `magento: src/Profile/Magento20/Gateway/Local/Reader/Magento20CustomerGroupReader.php` |
| DataSet | `magento: src/Profile/Magento/DataSelection/DataSet/CustomerGroupDataSet.php` |
| DI wiring | `magento: src/DependencyInjection/magento.xml` (base + 1.9 concretes) + `magento20.xml … magento24.xml` (per 2.x version) |

**Product** (uses the intermediate) — the full chain is `MagentoConverter` →
`Magento/Converter/ProductConverter` (base logic) → `Magento2/Converter/Magento2ProductConverter`
(2.x delta) → `Magento20/Converter/Magento20ProductConverter` (`supports()`).

---

## Part C — How the profile plugs into the framework (DI tags)

The Magento plugin registers tagged services in **XML** (`magento: src/DependencyInjection/
magento.xml` for shared services/DataSets/DataSelections, `magento20.xml … magento24.xml` for the
per-version concrete readers/converters). The Assistant scans these tags via its registries and
drives the tagged services. (The Assistant's own profiles register the same tags from
`assistant: src/Resources/config/…` — PHP/YAML rather than XML, but the same tag names.)

| Tag | Consumed by (Assistant registry) | Magento provides |
|---|---|---|
| `shopware.migration.profile` | `ProfileRegistry` | `Magento19/20…24Profile` |
| `shopware.migration.gateway` | `GatewayRegistry` | `Magento2XLocalGateway` |
| `shopware.migration.reader` | `Gateway/Reader/ReaderRegistry` | per-entity Magento readers |
| `shopware.migration.converter` | `Converter/ConverterRegistry` | per-entity Magento converters |
| `shopware.migration.data_set` | `DataSelection/DataSet/DataSetRegistry` | Magento DataSets |
| `shopware.migration.data_selection` | `DataSelectionRegistry` | Magento DataSelections |
| `shopware.migration.pre_mapping_reader` | `PremappingReaderRegistry` | Magento premapping readers |
| `shopware.migration.writer` | `WriterRegistry` | (mostly reuses Assistant writers) |
| `shopware.migration.media_file_processor` | `MediaFileProcessorRegistry` | Magento media processor |

In the XML, concrete per-version services use `parent="<base service id>"` to inherit constructor
args; you mostly declare the new service id, its `parent`, the `ConnectionFactory` argument (readers),
and the tag.

---

## Part D — Admin UI & tests

**Admin UI** lives in the **Assistant** (`assistant: src/Resources/app/administration/` — the Vue3
wizard module: intro/source selection → connection → data selection → premapping → processing
screen → history, plus error-resolution modal). The Magento plugin contributes only its
**credential forms** (`magento: src/Resources/app/administration/src/component/profile/magento/local/
…credential-form/`) for the DB host/port/user/password/dbName + optional table prefix + shop URL.
Most backlog UX tickets (#10630–#10634, #10615, #10616, #10622) target the *Assistant* wizard, not
the Magento plugin.

**Tests.** The Assistant ships the reusable test double
`assistant: tests/Mock/Migration/Mapping/DummyMappingService.php`. Converter tests (in either repo)
follow the same fixture pattern: instantiate the converter with a `DummyMappingService` pre-seeded
with the mappings it will look up, feed a `_fixtures/<entity>_data.php` sample shaped like real
(Magento) rows, and assert on the `ConvertStruct`. See `extending.md` for the pattern. Backlog
#10625/#10640/#10637 track expanding coverage.
