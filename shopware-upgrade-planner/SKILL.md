---
name: shopware-upgrade-planner
description: Plan and investigate Shopware 6.6 to 6.7 upgrades using versioned upgrade guidance and project context. Use when a user asks what could break, how to prepare a 6.6-to-6.7 migration, how a plugin, theme, payment integration, or hosting setup may be affected, or wants an evidence-linked upgrade checklist.
---

# Shopware upgrade planner

Help the user build an advisory, editable upgrade plan for a Shopware 6.6 to 6.7 journey. This is an experimental, temporary planning skill. State that it cannot guarantee a complete or safe upgrade. Do not perform an upgrade, apply fixes, or change a project unless the user asks for those actions.

## 1. Establish the journey

Ask for the exact four-part current and target versions if they cannot be established from the project. Ask what is known about custom and third-party extensions, administration code, storefront themes, payment and other integrations, hosting, and deployment. Accept “unknown”; do not invent an inventory, project finding, or vendor compatibility.

The bundled evidence covers 6.6.10.0–6.6.10.31 to 6.7.0.0–6.7.16.0. For other journeys, do not assert coverage: look for authoritative version-specific evidence if access is available, state the limitation, and offer an evidence-gathering checklist.

## 2. Find and verify relevant evidence

Read [source policy](references/source-policy.md) before interpreting the bundled sources or an issue, and follow [privacy boundaries](references/privacy.md) before handling project information. Search the local guides with:

```bash
python3 <skill-directory>/scripts/search_sources.py --from-version 6.6.10.0 --to-version 6.7.0.0 --query 'payment handler'
```

Replace the example versions and query with the user's journey and specific topic. Run focused searches for relevant administration, storefront, payment, API, hosting and configuration changes. The script returns ranked candidates and links, not a complete risk register. Add `--include-issues` to search a small set of unreviewed, generic issue leads; open and verify promising issues before using them. Use only generic, non-sensitive search terms. Prefer `--query-stdin` when a shell or process list may expose arguments; it does not make sensitive queries safe. Read each returned passage in its source before relying on it. When available, check the exact target-tag guide, related official migration guidance and release notes. Verify current issue or PR status against the primary source.

Distinguish when a warning was published, when a change takes effect, and whether it was withdrawn, superseded or changed. A later snapshot may revise historical entries and can contain later announcements: do not present them as changes already in the target. The 6.6 guide is contextual, not a list of new changes that occurred after the user's installed version. If the exact tagged evidence or current status is unavailable, state that explicitly.

## 3. Combine documentation and project context

A user must explicitly opt in before any project inspection or external AI use. Before inspecting files, tell them what will be inspected, what may be sent to the agent or its providers, and any unknowns about storage or location. Avoid production databases, dumps, customer records, transaction data, logs, credentials, environment files and secrets. Prefer synthetic examples and minimal metadata; if a source file may contain personal data, do not transmit it to a model or service without an approved, documented basis and safeguards. Redaction is fallible. Distinguish observed file paths from user-reported or inferred information and avoid exposing local paths. Reuse existing `shopware-cli project upgrade` readiness and compatibility checks and `project fix` / `extension fix` where applicable; verify the installed CLI's help and version first. Prefer read-only checks and supported dry runs. If an available Shopware language-server build can provide relevant diagnostics, use its results as additional evidence; record its version and scope. Do not claim any check or fix exists, ran, or proved compatibility without evidence.

The bundled search script reads local files and has no network or telemetry integration. The agent, AI provider, terminal and any tools may process or retain prompts, outputs and files separately; do not claim the overall workflow is local or private without verifying its configuration. Do not collect telemetry or create identifiers as part of this prototype. A documentation-only plan needs no running shop. Do not modify source, config, dependencies, databases, or deployment state as part of planning.

## 4. Produce and maintain the plan

Give a prioritized, adjustable sequence: inventory and unknowns; backup and test environment; compatibility and hosting; extension, theme and integration work; rehearsal and critical-flow tests; production deployment, verification and recovery. Tailor rather than blindly include every category.

For each step include the action, why it matters, owner, dependency or timing, evidence link and status. Label applicability as **observed**, **user-reported**, **possible—check**, or **unknown**. Separate source-code detections from operational and behavioral checks. Include relevant file paths only if actually observed. State coverage gaps and unresolved contradictions. Let the user mark steps done, not applicable, or needs investigation, and update the plan when facts change.

For a third-party payment integration, ask the vendor for target-version compatibility and test the real payment flows; do not assume its implementation from its existence. Highlight the consequences of credential or JWT transitions rather than instructing secret rotation without a specific migration plan.

Do not save plans or conversation transcripts automatically; if requested, use a user-chosen location, minimize sensitive content and explain that the host controls access, retention and deletion. Do not upload plans or project information without explicit authorization. Use [plan template](assets/plan-template.md) when an editable file is requested. Give concise answers to follow-up questions with source links and version scope. An editable plan can be returned in chat; create a file only when requested or needed for the user's workflow.
