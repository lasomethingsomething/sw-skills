#!/usr/bin/env python3
"""Prepare and summarize a small, human-reviewed paired skill experiment."""
import argparse
import json
from pathlib import Path
import random
import secrets
import sys

SUITE = Path(__file__).resolve().parents[2] / 'shopware-upgrade-planner/evals/scenarios.json'
RESULTS = {'pass', 'fail', 'not_run'}
COMPARISONS = {'no_skill': ('with_skill', 'without_skill'),
               'previous': ('candidate', 'previous')}


def prepare(suite, scenario_id, output, seed, comparison='no_skill'):
    scenarios = [s for s in suite['scenarios'] if s['id'] == scenario_id]
    if len(scenarios) != 1:
        raise ValueError(f'Unknown or duplicate scenario: {scenario_id}')
    scenario = scenarios[0]
    arms = list(COMPARISONS[comparison])
    random.Random(seed).shuffle(arms)
    # Do not overwrite existing evidence; permissions limit casual disclosure.
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    assignment = {'schema_version': 1, 'scenario_id': scenario_id, 'seed': seed, 'comparison': comparison,
                  'A': arms[0], 'B': arms[1]}
    scorecard = {'schema_version': 1, 'scenario_id': scenario_id,
                 'criteria': [{'id': c['id'], 'criterion': c['criterion'],
                               'A': 'not_run', 'B': 'not_run', 'notes': ''}
                              for c in scenario['criteria']]}
    for name, content in [('prompt.txt', scenario['prompt'] + '\n'),
                          ('assignment.json', json.dumps(assignment, indent=2) + '\n'),
                          ('scorecard.json', json.dumps(scorecard, indent=2) + '\n')]:
        path = output / name
        with path.open('x', encoding='utf-8') as stream:
            path.chmod(0o600)
            stream.write(content)
    return {'scenario_id': scenario_id, 'files': ['prompt.txt', 'assignment.json', 'scorecard.json'],
            'notice': 'No agent has been run and every criterion is not_run.'}


def summarize(assignment, scorecard, suite):
    if assignment.get('schema_version') != 1 or scorecard.get('schema_version') != 1:
        raise ValueError('Unsupported assignment or scorecard schema.')
    arms = COMPARISONS.get(assignment.get('comparison'))
    if arms is None or set((assignment.get('A'), assignment.get('B'))) != set(arms):
        raise ValueError('Assignment must contain both arms for the selected comparison.')
    if scorecard.get('scenario_id') != assignment.get('scenario_id'):
        raise ValueError('Assignment and scorecard scenarios do not match.')
    scenarios = [s for s in suite['scenarios'] if s['id'] == assignment['scenario_id']]
    if len(scenarios) != 1:
        raise ValueError('Scenario no longer matches the suite used for scoring.')
    expected = {c['id']: c['criterion'] for c in scenarios[0]['criteria']}
    rows = scorecard.get('criteria')
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError('Scorecard must contain every criterion once.')
    seen, paired = set(), []
    counts = {arm: {'pass': 0, 'fail': 0, 'not_run': 0} for arm in arms}
    for row in rows:
        cid = row.get('id')
        if cid not in expected or cid in seen or row.get('criterion') != expected[cid]:
            raise ValueError('Scorecard criteria must match the scenario exactly.')
        seen.add(cid)
        for label in ('A', 'B'):
            result = row.get(label)
            if result not in RESULTS:
                raise ValueError('Ratings must be pass, fail, or not_run.')
            counts[assignment[label]][result] += 1
        if 'not_run' not in (row['A'], row['B']):
            outcomes = {assignment[label]: row[label] for label in ('A', 'B')}
            paired.append({'criterion_id': cid, **outcomes})
    return {'scenario_id': assignment['scenario_id'], 'criteria': len(expected),
            'completed_pairs': len(paired), 'counts': counts, 'paired_results': paired,
            'notice': 'Human ratings only; a small synthetic comparison does not establish real-world effectiveness or safety.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare', help='Create an unscored paired scenario locally.')
    p.add_argument('--scenario', required=True)
    p.add_argument('--output-dir', required=True, type=Path)
    p.add_argument('--seed', type=int, help='Optional reproducible random assignment seed.')
    p.add_argument('--comparison', choices=tuple(COMPARISONS), default='no_skill',
                   help='Compare the skill to no skill (default) or a candidate to the previous skill.')
    p = sub.add_parser('summarize', help='Summarize a manually completed scorecard.')
    p.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        suite = json.loads(SUITE.read_text(encoding='utf-8'))
        if args.action == 'prepare':
            result = prepare(suite, args.scenario, args.output_dir,
                             args.seed if args.seed is not None else secrets.randbits(64), args.comparison)
        else:
            result = summarize(json.loads((args.run_dir / 'assignment.json').read_text(encoding='utf-8')),
                               json.loads((args.run_dir / 'scorecard.json').read_text(encoding='utf-8')), suite)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'Cannot {args.action}: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
