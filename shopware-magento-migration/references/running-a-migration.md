# Running a Magento → Shopware 6 migration

The operational path: install **both** plugins, connect to the Magento database, premap, and run —
without getting ambushed by scale. Read `known-issues.md` alongside this; the gotchas referenced
here are detailed there. Throughout, remember the two layers (`architecture.md`): the **Assistant**
is the runtime/wizard/queue; the **Magento profile** is the source adapter.

## Prerequisites

- A **Shopware 6** target install you control the CLI on (`bin/console`), with a **worker / message
  queue running** — the migration is queue-driven and will appear to hang at 0% without it.
- Both plugins installed and active:
  - **SwagMigrationAssistant** — the free base framework (the Magento plugin requires it;
    `magento: composer.json` → `swag/migration-assistant`).
  - **SwagMigrationMagento** — the Magento source profile (this is the one that adds "Magento" to the
    source dropdown).
- **Direct network + DB access from the Shopware server to the Magento MySQL database.** Magento uses
  the **local gateway** — it connects straight to Magento's DB. There is no API option, and the
  "Migration Connector" plugin in the docs is **only for Shopware-5 sources** — not Magento. If the
  Magento DB isn't reachable from Shopware, open a tunnel or run from a host that can reach both.
- The **Magento media files** reachable (filesystem path or shop URL) so media can be fetched.
- Know your **source Magento version (1.9 or 2.0–2.4)** — you pick a matching profile, and the wrong
  one silently mis-reads schema differences (notably the password encoder).
- Version-compatibility: check `magento: composer.json` (`shopware/core`, `swag/migration-assistant`
  constraints) against your Shopware version; the README recommends current trunk branches when
  working against unreleased Shopware.

## Install the plugins

From the Shopware root:

```sh
# the Magento profile (and the Assistant, if not already present)
git clone https://github.com/shopware/SwagMigrationMagento.git custom/plugins/SwagMigrationMagento

bin/console plugin:refresh
bin/console plugin:install --activate SwagMigrationAssistant   # framework — if not already active
bin/console plugin:install --activate SwagMigrationMagento     # Magento profile
bin/console cache:clear
```

Then build the administration so the Magento profile + its credential forms appear:

```sh
bin/build-administration.sh        # or your project's admin build step
```

## Create a Magento connection

In the Shopware admin: **Settings → (Extensions →) Migration Assistant** (the dashboard card was
removed — #10622 — so go via Settings). This wizard is the **Assistant's** UI; the Magento plugin
only adds the profile option and the credential fields.

1. Create a **connection**, pick the **Magento** profile + your version (1.9 / 2.0–2.4).
2. Gateway is **Local** (the only option for Magento). Fill the credential form: Magento DB **host,
   port, user, password, database name**, optional **table prefix**, and the **shop URL** (used for
   media + SEO URLs).
3. The plugin runs an **environment check** (`EnvironmentReader`) — it validates the connection and
   table prefix and reads currencies. Wrong table prefix → reads return nothing; fix it here.

Only run **one connection at a time** — two active connections can cause mapping collisions, and
there's no hard guard yet (#10643).

## Premapping (do it deliberately, once)

Before the run the wizard shows **premapping** — Magento source values it can't auto-resolve, for
you to map by hand: salutations, **payment methods**, **shipping methods**, order/transaction/
delivery states, tax classes. The premapping *engine* is the Assistant's; the *list of what needs
mapping* comes from the Magento profile's premapping readers. It's manual and tedious (payment
methods especially — #10607), but it's the contract that makes converted orders reference real
Shopware methods. Map everything; an unmapped value blocks or mis-assigns dependents.

## Select what to migrate (and in what order)

Data is selected as **DataSelections** (grouped bundles), not individual entities — *Basic settings*,
*Products*, *Customers & orders*, *Media*, *Reviews*, *SEO URLs*. You can't cherry-pick a single
DataSet within a selection (#10644). Order matters and is enforced by dependencies — run
foundational selections first so their mappings exist before dependents:

```text
Basic settings (languages, currencies, customer groups, countries, shop structure)
  → Products (+ manufacturers, properties, reviews)
  → Customers & orders
  → Media
  → SEO URLs
```

On a **re-run** the current model re-fetches already-done dependencies (the motivation for #10644);
plan re-runs accordingly.

## Running the migration (it's queue-driven)

The Assistant advances the run through its **step state machine** (`fetching → writing →
media-processing → indexing`; see `architecture.md`) by dispatching **message-queue** messages. You
**must** have workers consuming the queue, or it sits at 0%. Either keep the admin tab open (it
drives the queue in the foreground) **and/or** run CLI workers:

```sh
bin/console messenger:consume async --time-limit=600 --memory-limit=512M   # run several in parallel for throughput
```

Watch `swag_migration_run` for step/progress and the migration log (admin history) for per-record
errors.

## Before a big migration: apply the known mitigations

Real Magento shops (hundreds of thousands → millions of orders/customers/products) hit predictable
walls. Do these up front — details and issue links in `known-issues.md`:

- **Check the `swag_migration_data` index** — `SHOW INDEX FROM swag_migration_data`. The
  `(entity, run_id, convert_failure)` index that keeps convert lookups fast has shipped since 2019,
  so it's normally already present; only add `assets/swag_migration_data-index.sql` on older installs
  or if `EXPLAIN` shows the `ORDER BY` sort is the cost (#10647).
- **Expect slow Magento reads at high offsets.** Offset pagination degrades as the offset grows; 1M+
  orders can blow past web-server timeouts (#10645, #10642). Prefer the **CLI worker** (no nginx 90s
  ceiling) over the foreground/admin-driven queue, raise PHP/DB timeouts, and migrate in narrower
  batches.
- **Give PHP and MySQL generous timeouts and memory** for the worker processes.
- **Snapshot the Shopware target DB** before each attempt so a failed run is a clean restore.

## Troubleshooting: symptom → layer → action

| Symptom | Layer | What to check / do |
|---|---|---|
| Run stuck at 0%, nothing progresses | Assistant (queue) | No worker consuming `async`. Start `messenger:consume` or keep the admin tab open. |
| Reads time out (~90s) on orders/customers | Magento (Reader SQL) + web timeout | Run via CLI worker not the browser; raise timeouts; #10645/#10642. |
| Convert phase crawls for many minutes | Assistant (`swag_migration_data` / mapping) | Apply `assets/swag_migration_data-index.sql` (#10647); MappingService load #10627/#10628. |
| `SQLSTATE` write error referencing a missing id | Magento convert → write dependency | A dependency failed to convert; the dependent shouldn't be written (#10649). Re-run the dependency selection first. |
| Default customer group not set as default in SW6 | Magento (converter/mapping) | Known: default flag not carried; set it manually post-migration (#10646). |
| Variant/configurator images missing in storefront | Magento (product/media converter) | Known limitation; not applied to storefront variant display (#10648). |
| Payment/shipping methods unassigned or wrong | Assistant premapping (Magento list) | Re-check premapping; mapping is manual (#10607). |
| Old Magento passwords don't work after login | Magento (PasswordEncoder) | Verify the profile matches the Magento version; encoders differ (Md5/Sha256/Argon2Id13) (#10650). |
| Custom fields have an ugly fixed prefix | Magento (converter, by design) | Prefix not configurable yet (#10617); rename post-migration. |
| Old URLs 404 after go-live | Magento (SEO URLs) | 301 redirects for changed URLs aren't auto-created (#10618); set them up yourself. |
| Re-run re-migrates everything / odd duplicates | Assistant (checksums + `swag_migration_data` reset) | Housekeeping has rough edges (#10639, #10626); avoid manual table edits, restore from snapshot. |

## After the migration

- Spot-check high-value entities (a configurable product + variants, a customer with orders, a
  category tree, media) against the Magento source.
- Re-flag the **default customer group** and default sales-channel settings the migration doesn't
  carry (#10646).
- Set up **301 redirects** from old Magento URLs if SEO continuity matters (#10618).
- Verify the migrated storefront renders, and check visual regressions and accessibility.
  A visual baseline right after migration helps catch unexpected changes.
