# Checklist: add a new entity to the Magento → Shopware 6 migration

Paste into a PR description and tick off. Details and code in `references/extending.md`.
Replace `MyEntity` / `MY_ENTITY` with your entity. Put the base logic in `src/Profile/Magento/` (it
serves all versions); add an optional `src/Profile/Magento2/` subclass **only** if behaviour must
differ across all of 2.x vs 1.9; version-specific concretes go in `src/Profile/Magento20…24/` (and
`Magento19/`).

## Code

- [ ] **DataSet** — `src/Profile/Magento/DataSelection/DataSet/MyEntityDataSet.php`
      (`getEntity()` returns the entity key; `supports()` checks `MagentoProfileInterface`).
- [ ] **Reader (base)** — `src/Profile/Magento/Gateway/Local/Reader/MyEntityReader.php`
      (`extends AbstractReader`; implement `read()` and `readTotal()`).
- [ ] **Reader (per version)** — `Magento2X/Gateway/Local/Reader/Magento2XMyEntityReader.php`
      for each supported version (version SQL, or inherit base if identical).
- [ ] **Converter (base)** — `src/Profile/Magento/Converter/MyEntityConverter.php`
      (`extends MagentoConverter`; `convert()` body from `assets/skeletons/MyEntityConverter.php`).
      Add a `src/Profile/Magento2/` subclass only if a 2.x-vs-1.9 behaviour split needs it.
- [ ] **Converter (per version)** — `Magento2X/Converter/Magento2XMyEntityConverter.php`
      for each supported version (usually just `supports()`).
- [ ] **DataSelection** — add `MyEntityDataSet` to the right DataSelection in
      `src/Profile/Magento/DataSelection/`, in dependency order (after entities it references).
- [ ] **Premapping** (only if it references unresolvable values) — reader under
      `src/Profile/Magento/Premapping/`.

## DI registration (tags)

- [ ] DataSet registered in `magento.xml` with `shopware.migration.data_set`.
- [ ] DataSelection registered in `magento.xml` with `shopware.migration.data_selection` (if new).
- [ ] Concrete Reader registered in **each** `magento20.xml … magento24.xml` with
      `shopware.migration.reader`, `parent="…\Magento\…\MyEntityReader"`, `ConnectionFactory` arg.
- [ ] Concrete Converter registered in **each** `magento20.xml … magento24.xml` with
      `shopware.migration.converter`, `parent="…\Magento\Converter\MyEntityConverter"`.

## Converter correctness (review gates)

- [ ] Every old Magento id resolved to a UUID via `mappingService` (`getOrCreateMapping` for the
      entity itself, `getMapping` for foreign references).
- [ ] Foreign reference missing → **skip the record** (return `ConvertStruct(null, $data)` + log),
      never write a dangling reference (avoids the shopware/shopware#10649 cascade).
- [ ] Leftover/unconsumed source data returned as the 2nd `ConvertStruct` argument.
- [ ] Fields copied with `convertValue()` using the correct `TYPE_*` constant.
- [ ] EAV null-vs-missing handled (guard before reading attribute values).
- [ ] Reads avoid naive `LIMIT … OFFSET …` on huge tables where possible (perf cliff
      shopware/shopware#10645 / #10642).

## Tests

- [ ] Converter test under `tests/` using a `DummyMagentoMappingService` pre-seeded with every
      mapping the converter looks up.
- [ ] `_fixtures/my_entity_data.php` sample shaped like real (anonymised) Magento output.
- [ ] Assertions: converted payload fields, consumed source fields removed, and the
      missing-dependency path returns null converted data.

## Manual verification

- [ ] Run a small migration including the new entity; confirm the DataSet appears in its
      DataSelection and the count (`readTotal`) is right.
- [ ] Spot-check a migrated record against the Magento source.
- [ ] Confirm cross-references resolve (the entity links to its already-migrated dependencies).
