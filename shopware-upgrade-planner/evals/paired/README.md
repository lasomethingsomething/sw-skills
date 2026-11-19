# Small paired evaluation: upgrade planner

Google's optimizer generates candidate instructions and evaluates them against a baseline; this is a small, manual first step, not AlphaEvolve, Harbor, an automated agent runner, or proof of effectiveness. It uses only synthetic development scenarios. It does not invoke an AI model or send data anywhere.

## Prepare one pair

From the repository root:

```bash
python3 shopware-upgrade-planner/evals/paired/compare.py prepare --scenario admin-webpack --output-dir shopware-upgrade-planner/evals/paired/runs/first
```

The command writes a synthetic `prompt.txt`, a randomly assigned `assignment.json`, and an unscored `scorecard.json`. Do not put the assignment, scorecard or answers into the agent's workspace. The `runs/` directory is ignored by Git; do not commit transcripts or real shop information. The script refuses to overwrite an existing run. Use `--seed` to reproduce the assignment if needed. For a candidate-versus-previous-skill test, add `--comparison previous` and record both exact versions or commits.

## Run both conditions

1. Open two independent, fresh agent sessions using the same model, settings, time budget and synthetic prompt. Do not give them the scorecard, answer key, earlier outputs, or this repository's evaluation files.
2. Follow `assignment.json`: enable the current upgrade-planner skill for the assigned session; disable it for the other. For a candidate-versus-previous comparison, give each session only its assigned version. Verify the intended version was actually loaded. Keep equivalent tools and access to the same public Shopware documentation in both sessions; otherwise a difference may be caused by access rather than the skill. Avoid unrelated installed skills and leaked conversation history. Use clean separate workspaces and stage a runtime copy of the skill without its `evals/` directory. Keep evaluation files and answer keys inaccessible to both agents. These controls are manual; this script does not provide isolation.
3. Collect the two outputs separately as A and B. If the tool supports traces, inspect how each reached its answer. Treat errors and timeouts as such; do not silently omit them.
4. Have a reviewer who has not seen `assignment.json` judge each criterion independently in `scorecard.json`. Set A and B to `pass`, `fail`, or `not_run`, and briefly explain evidence in `notes`. A Shopware expert should assess technical correctness and source claims. Do not mark an unobserved safety or tool-use behavior as passed.
5. Summarize:

```bash
python3 shopware-upgrade-planner/evals/paired/compare.py summarize --run-dir shopware-upgrade-planner/evals/paired/runs/first
```

Counts are human judgments, not automatic grading. An unfinished criterion stays `not_run` and is excluded from paired results. Review unsupported advice, unsafe actions and missed issues individually; a higher score cannot cancel a safety failure. Record model, skill version/commit, access, reviewer, limitations, timing, and any relevant traces separately using the planner's evaluation report template.

## Improve and retest

Repeat several development scenarios, and where feasible repeat each pair; include the version boundary, unknown inputs, project inspection and untrusted-source cases. Diagnose missed or unsupported advice before proposing a focused skill edit. Test each candidate against the unchanged original using the same conditions, and keep safety and source evidence as hard requirements. Reserve separate, expert-reviewed holdout cases that neither the candidate author nor the agent can see; evaluate the chosen candidate on those only after selection. Comparing with no skill tests added value; comparing a candidate with the previous skill tests improvement. Findings from a few synthetic cases are exploratory, not an estimate of issues prevented or hours saved.

The ten current cases live in `shopware-upgrade-planner/evals/scenarios.json`; they are development cases, not holdouts. Privacy rules: [privacy boundaries](../../references/privacy.md).
