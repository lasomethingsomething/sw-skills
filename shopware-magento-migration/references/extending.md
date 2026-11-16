# Extending the migration: add an entity, fix a converter

Read `architecture.md` first — this assumes you know the Profile / Gateway / Reader / Converter /
DataSet / DataSelection / MappingService roles and the base-vs-version layering.

**You work in the Magento profile plugin (SwagMigrationMagento), subclassing the Assistant's base
classes.** The framework (SwagMigrationAssistant) supplies `Converter`, `DataSet`,
`DataSelectionInterface`, `ReaderInterface`, `MappingService`, the premapping/writer/media bases, and
the registries that discover your tagged services; you supply the Magento-specific SQL and mapping
logic. All paths below are in the Magento repo unless prefixed `assistant:`.

## Adding support for a new entity (end to end)

Say Magento has an entity the profile doesn't migrate yet. You'll create the shared logic in the
right base layer, then a thin concrete subclass per supported version, then register everything in
DI. Use `assets/skeletons/` as starting templates and `assets/new-entity-checklist.md` as the PR
checklist.

**Pick the base layer first (the three tiers):**
- **`src/Profile/Magento/…`** — the all-versions base. Put your real converter/reader logic here; it
  serves 1.9 and every 2.x version. This is the default and where the examples below go.
- **`src/Profile/Magento2/…`** — an *optional* intermediate, only if part of the behaviour must
  differ across all of 2.x vs 1.9. It subclasses the all-versions base (`Magento2ProductConverter
  extends ProductConverter`); only Product, Customer, Order, SalesChannel have one today. Skip it
  unless you need it.
- **`src/Profile/Magento20…24/`** (and `Magento19/`) — per-version concretes, usually just
  `supports()`, extending the closest base above.

Default to `Profile/Magento/`; reach for `Profile/Magento2/` only for a genuine 2.x-vs-1.9 split.

### 1. DataSet — declare the entity
`src/Profile/Magento/DataSelection/DataSet/MyEntityDataSet.php`:

```php
class MyEntityDataSet extends DataSet
{
    public static function getEntity(): string { return DefaultEntities::MY_ENTITY; } // string key, used everywhere
    public function supports(MigrationContextInterface $migrationContext): bool {
        return $migrationContext->getProfile() instanceof MagentoProfileInterface;
    }
}
```
The `getEntity()` string is the join key across Reader, Converter, and the mapping table. If it's a
Shopware-known entity, reuse the `DefaultEntities::` constant; otherwise define one.

### 2. Reader — pull it from Magento
Abstract base `src/Profile/Magento/Gateway/Local/Reader/MyEntityReader.php extends AbstractReader`,
implementing `read()` (the SQL) and ideally `readTotal()` (count, for the progress bar). Then a
concrete reader per version, `src/Profile/Magento2X/Gateway/Local/Reader/Magento2XMyEntityReader.php`,
holding the version's SQL (or just inheriting the base if the schema is identical across versions).

**Watch the EAV joins and pagination.** If your entity is attribute-heavy (product/customer-like),
you'll join `*_entity` against `*_entity_{varchar,int,decimal,…}` on attribute ids. Avoid naive
`LIMIT … OFFSET …` on huge tables — that's the documented performance cliff (#10645, #10642).

### 3. Converter — Magento row → Shopware payload
Abstract base `src/Profile/Magento/Converter/MyEntityConverter.php extends MagentoConverter`.

**The full annotated `convert()` body lives in one place: `assets/skeletons/MyEntityConverter.php`.**
Copy that as your starting point rather than re-keying it here (kept single-source so it can't drift
from the skeleton). For a real reference implementation, read the closest existing converter in
`src/Profile/Magento/Converter/` (e.g. `CustomerGroupConverter`).

Concrete subclass per version — usually just `supports()`:
```php
class Magento20MyEntityConverter extends MyEntityConverter {
    public function supports(MigrationContextInterface $migrationContext): bool {
        return $migrationContext->getProfile() instanceof Magento20Profile
            && $this->getDataSetEntity($migrationContext) === MyEntityDataSet::getEntity();
    }
}
```

Rules that keep converters correct (the skeleton encodes all of these):
- **Every old id → UUID goes through the MappingService.** Never invent ids.
- **Look up foreign references; skip the record if the dependency is missing** rather than writing a
  dangling row (the cascade in #10649).
- **Return leftover data** as the 2nd `ConvertStruct` arg so nothing is silently dropped.
- Use `convertValue()` with the right `TYPE_*` constant for type-casting.

### 4. Attach to a DataSelection
Add `MyEntityDataSet` to the relevant DataSelection in `src/Profile/Magento/DataSelection/`
(`ProductDataSelection`, `CustomerAndOrderDataSelection`, etc.) **in dependency order** — after the
entities yours references. If it's a brand-new grouping, create a new DataSelection class and tag it.

### 5. Register in DI — once per version
The DI files are `magento.xml` plus `magento20.xml … magento24.xml` (there is **no** `magento19.xml`
or `magento2.xml` — see below).
- Shared services (the all-versions base, any `Magento2` intermediate), the DataSet, the
  DataSelection, **and the Magento 1.9 concrete services** go in `src/DependencyInjection/magento.xml`.
- The concrete **2.x** per-version Reader and Converter go in **each** of `magento20.xml …
  magento24.xml`. Concrete services use `parent="<base service id>"` to inherit constructor args.
  Pattern (from `magento20.xml`):

```xml
<service id="Swag\MigrationMagento\Profile\Magento20\Gateway\Local\Reader\Magento20MyEntityReader"
         parent="Swag\MigrationMagento\Profile\Magento\Gateway\Local\Reader\MyEntityReader">
    <argument type="service" id="Swag\MigrationMagento\Profile\Magento\Gateway\Connection\ConnectionFactory"/>
    <tag name="shopware.migration.reader"/>
</service>

<service id="Swag\MigrationMagento\Profile\Magento20\Converter\Magento20MyEntityConverter"
         parent="Swag\MigrationMagento\Profile\Magento\Converter\MyEntityConverter">
    <tag name="shopware.migration.converter"/>
</service>
```
DataSet (in `magento.xml`):
```xml
<service id="Swag\MigrationMagento\Profile\Magento\DataSelection\DataSet\MyEntityDataSet">
    <tag name="shopware.migration.data_set"/>
</service>
```

Tag reference: `shopware.migration.profile`, `.gateway`, `.reader`, `.converter`, `.data_set`,
`.data_selection`, `.pre_mapping_reader`, `.writer`, `.media_file_processor`.

### 6. Premapping (only if needed)
If your entity references a value that can't be auto-resolved to a Shopware target (a method, a
state, a salutation), add a pre-mapping reader under `src/Profile/Magento/Premapping/` tagged
`shopware.migration.pre_mapping_reader`, and resolve it in the converter via the mapping it produces.

### 7. Test it (fixture pattern, no live DB)
Mirror the converter-test pattern under `tests/`. The framework ships a reusable double,
`assistant: tests/Mock/Migration/Mapping/DummyMappingService.php` (the Magento repo uses its own
`DummyMagentoMappingService` wrapper) — use whichever the Magento test base exposes:
- Instantiate the converter with the **dummy mapping service** pre-seeded with the mappings the
  converter will look up (the parent entity, currency, language, tax — whatever `getMapping()` is
  called for).
- Feed `convert()` a sample row from `tests/.../_fixtures/<entity>_data.php` shaped like real Magento
  output (copy a real row, anonymised).
- Assert on the `ConvertStruct`: the converted payload fields, that consumed source fields are gone,
  and that a missing-dependency case returns `null` converted data rather than a dangling record.

This is exactly the gap #10625 is about (lookup-service data not specified in tests) — seed your
lookups explicitly.

## Fixing a converter (mapping data wrong)

1. **Reproduce in a test, not the UI.** Grab the offending Magento row into a `_fixtures` file and
   write/extend a converter test that demonstrates the wrong output. Far faster than re-running a
   migration.
2. **Locate the layer.** Wrong/missing *field* → the base converter body. Wrong *cross-reference* →
   a `getMapping()` lookup or a missing premapping. *Crash on write* → a dangling reference that
   should have been skipped (#10649).
3. **Fix in the lowest base that's wrong.** Usually that's the all-versions base
   `Profile/Magento/Converter/…`, so the fix benefits 1.9 and every 2.x version. Only fix in a
   `Profile/Magento2/…` intermediate if the bug is in the 2.x-specific behaviour, or in a
   `Magento20…24` subclass if it's genuinely one version.
4. **Mind EAV null-vs-empty.** Magento attribute tables often have absent rows rather than NULLs;
   guard `isset()`/defaults before `convertValue()`.

## Adding a new Magento version profile

The version dirs (`Magento20…24`) are the template: a `…Profile` subclass of `Magento2Profile` (set
`SOURCE_SYSTEM_VERSION`), concrete Readers/Converters subclassing the `Profile/Magento/` bases (only
where SQL/logic differs), a `…LocalGateway`, and a new `magentoXX.xml` DI file plus a credential-form
component under `Resources/app/administration/…`. Copy the closest existing version and adjust the
schema-specific SQL and the password encoder.
