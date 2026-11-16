-- Slow customer/convert lookups during large migrations.
-- Source: Migration Assistant backlog, shopware/shopware#10647.
--
-- Symptom: during the convert phase the Assistant repeatedly runs queries like
--   SELECT id FROM swag_migration_data
--   WHERE entity = 'customer' AND run_id = ? AND convert_failure = 0
--   ORDER BY auto_increment ASC LIMIT 100 OFFSET <large>;
-- On large datasets, an unindexed variant of this examined hundreds of thousands
-- of rows per page and ran for ~20 minutes (one observed query: Rows_examined 256313).
--
-- IMPORTANT — read before applying:
-- The Assistant ALREADY ships a composite index on (entity, run_id, convert_failure)
-- via Migration1564053392AddConvertFailureKeyToData (added 2019-07-25), and a separate
-- index on (auto_increment). On any currently supported version (verified on
-- SwagMigrationAssistant 18.0 / Shopware 6.7) the filter is therefore already covered,
-- and `convert_failure` is a TINYINT(1), not an empty-string column.
--
-- So this file is NOT a "missing index" fix on current versions. It is only useful to:
--   1. installs predating the 2019 migration, or
--   2. cases where profiling (EXPLAIN / slow log) shows the ORDER BY auto_increment sort
--      is the cost and you want a single index that covers both filter AND sort.
--
-- ALWAYS check what already exists first:
--   SHOW INDEX FROM swag_migration_data;
-- If `idx.swag_migration_data.entity__run_id__convert_failure` is present, you very
-- likely do NOT need this; confirm with EXPLAIN before adding a redundant index.
--
-- Apply against the SHOPWARE 6 (target) database. Safe to run once; building it on a
-- populated table takes a moment.

CREATE INDEX swag_migration_data_entity_run_convert_sort_idx
    ON swag_migration_data (entity, run_id, convert_failure, auto_increment);

-- To remove it again:
--   DROP INDEX swag_migration_data_entity_run_convert_sort_idx ON swag_migration_data;
