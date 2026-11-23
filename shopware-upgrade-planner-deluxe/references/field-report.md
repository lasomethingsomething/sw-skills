# Field report: one real 6.6 → 6.7 migration

Lessons from a [public retrospective of one project's upgrade](https://gist.github.com/shyim/c4d5b9d0bf8da46f7040405a7cd8e228) (6.6.10.5 → 6.7.0.1, 2025). One project is one data point: use it to find areas to check and to shape the plan, never as proof that another project is affected. Paraphrased here; the counts belong to that project.

Read this file when you build the plan (workflow step 5) and when you check it (step 6).

## Changes that the guide or core source confirms

Cite the guide, not the report, for these.

| Change | Evidence |
| --- | --- |
| `EntityExtension::getDefinitionClass()` removed; `getEntityName()` is abstract and required | `UPGRADE-6.7.md` at v6.7.0.0, "Removed EntityExtension::getDefinitionClass" |
| `ScheduledTaskHandler` needs a `LoggerInterface` as its second constructor argument | [core source at v6.7.0.0](https://github.com/shopware/shopware/blob/v6.7.0.0/src/Core/Framework/MessageQueue/ScheduledTask/ScheduledTaskHandler.php); guide note only in the 6.7.16.1 snapshot, not the v6.7.0.0 one |
| `StorefrontController::setTwig` removed: delete the `setTwig` calls from service config | `UPGRADE-6.7.md` at v6.7.0.0, "Removal of `setTwig` method" |
| `page.header` / `page.footer` removed from `Page`; header and footer are pagelets | `UPGRADE-6.7.md` at v6.7.0.0, the pagelet and template-variable notes |
| `technicalName` required for payment and shipping methods | `UPGRADE-6.7.md` at v6.7.0.0, "New `technicalName` property" |
| DBAL 4 (for example `executeUpdate()` → `executeStatement()`) | `UPGRADE-6.7.md` at v6.7.0.0, "Major Library Updates" links the DBAL upgrade guide |

## Seen in that project, not confirmed for every project

Label these "possible—check" in the plan.

- **PHP:** `TaggedIterator` → `AutowireIterator`; `StoreApiResponse` subclasses that redeclare `$object`; `Context::createDefaultContext(new SystemSource())` calls rewritten; import/export profiles needing a technical name; custom Store-API cache decorators replaced by the cache-tag event; custom document renderers adapted.
- **Administration (the largest surface there):** `sw-*` → `mt-*` components (text field, button, card, icon, number field, switch, textarea, select), `value` / `update:value` → `model-value` / `v-model`, `$set()` removed, `Shopware.Store` instead of Vuex helpers, SCSS selectors on old components, overridden admin templates compared with their changed core versions. Not every `sw-*` component has a one-to-one `mt-*` replacement.
- **Storefront:** core template drift in address management, header, account, checkout, product card, configurator, payment, shipping, alert, modal and navigation templates; forms moved to `data-form-handler`; renamed blocks and `shopware-block` references; listing filter markup; accessibility markup (lists, button-links, stretched links). Some templates compiled but broke visually (click areas, z-index): a build doesn't prove they work.
- **Dependencies and operations:** a locally bundled plugin replaced by its compatible Store package; obsolete patches, cache and JWT config keys removed; filesystem config lost in the config migration and restored; `system:update:finish` added to database refresh and deployment preparation.

## Plan practices

Add these to the plan where they apply.

1. **Dependency report first.** Before changing the Shopware constraint, run `composer why-not shopware/core <target>` (with consent, like any command) and classify each blocking package as upgrade, replace, remove or patch. Check that every Store package is available to the production build.
2. **Separate commits:** formatting and codemods; dependencies and config; PHP API; Administration; Storefront; data migrations and project behaviour. In that project, a formatting commit touched 375 files right before the real migration, which made review harder.
3. **Upgrade CI gate before merge:** install on the target version; fresh install and boot; DAL validation; static analysis and tests; `shopware-cli project validate`; production Administration build; production Storefront build; import a sanitized database from the old version, run migrations and `system:update:finish`; browser smoke tests. That project's CI had no production Administration build, and most of its post-merge fixes were build and template problems.
4. **Smoke tests on what changed:** the Administration loads without errors, custom admin listings and detail pages, custom CMS elements save, listing filters, address management, add-to-cart and checkout forms, account and order pages, product-card click areas, accessibility scans of forms and listings.
5. **Expect most manual work in** custom caching, document rendering, data-migration semantics, plugin replacement and visual behaviour after template changes. Mechanical work (Rector rule sets for Shopware 6.7, Symfony and PHP; admin codemods) should go in its own commits.
