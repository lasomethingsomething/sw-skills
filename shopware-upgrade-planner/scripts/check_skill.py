#!/usr/bin/env python3
"""Validate the upgrade planner's local structure, version, links, and eval suite."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:
    print('PyYAML is required for validation: python3 -m pip install PyYAML==6.0.2', file=sys.stderr)
    sys.exit(2)

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parent
SEMVER = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')
IDENTIFIER = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
LINK = re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')


def parse_frontmatter(text):
    match = re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)', text, re.DOTALL)
    if not match:
        raise ValueError('SKILL.md must start with valid YAML frontmatter.')
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f'Invalid YAML frontmatter: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('Frontmatter must be a mapping.')
    return data


def version_tuple(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError('metadata.version must be a quoted three-part SemVer string.')
    return tuple(map(int, value.split('.')))


def check_metadata(text, name):
    data = parse_frontmatter(text)
    errors = []
    actual = data.get('name')
    if not isinstance(actual, str) or not IDENTIFIER.fullmatch(actual) or len(actual) > 64 or actual != name:
        errors.append('Skill name must match its folder and follow the Agent Skills naming rules.')
    desc = data.get('description')
    if not isinstance(desc, str) or not 1 <= len(desc.strip()) <= 1024:
        errors.append('Description must be a nonempty string of at most 1024 characters.')
    meta = data.get('metadata')
    if not isinstance(meta, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in meta.items()):
        errors.append('metadata must be a string-to-string mapping containing version.')
    else:
        try:
            version_tuple(meta.get('version'))
        except ValueError as exc:
            errors.append(str(exc))
    if len(text.splitlines()) > 500:
        errors.append('SKILL.md exceeds 500 lines.')
    return errors


def check_scenarios(document):
    errors = []
    if not isinstance(document, dict) or document.get('schema_version') != 1:
        return ['Evaluation suite must declare schema_version 1.']
    scenarios = document.get('scenarios')
    if not isinstance(scenarios, list) or not scenarios:
        return ['Evaluation suite must contain at least one scenario.']
    scenario_ids, prompts, criteria_ids = set(), set(), set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append('Each scenario must be an object.')
            continue
        sid, prompt, criteria = scenario.get('id'), scenario.get('prompt'), scenario.get('criteria')
        if not isinstance(sid, str) or not IDENTIFIER.fullmatch(sid) or sid in scenario_ids:
            errors.append('Scenario IDs must be unique lowercase hyphenated identifiers.')
        else:
            scenario_ids.add(sid)
        if not isinstance(prompt, str) or not prompt.strip() or prompt.strip() in prompts:
            errors.append('Scenario prompts must be nonempty and unique.')
        else:
            prompts.add(prompt.strip())
        if not isinstance(criteria, list) or not criteria:
            errors.append(f'Scenario {sid} needs at least one atomic criterion.')
            continue
        for criterion in criteria:
            if not isinstance(criterion, dict) or set(criterion) != {'id', 'criterion'}:
                errors.append(f'Scenario {sid} criteria must have exactly id and criterion.')
                continue
            cid, text = criterion['id'], criterion['criterion']
            if not isinstance(cid, str) or not IDENTIFIER.fullmatch(cid) or cid in criteria_ids:
                errors.append('Criterion IDs must be unique lowercase hyphenated identifiers.')
            else:
                criteria_ids.add(cid)
            if not isinstance(text, str) or not text.strip():
                errors.append(f'Criterion {cid} must be a nonempty string.')
    return errors


def check_relative_links(skill_dir):
    errors = []
    # Upstream snapshots are preserved byte-for-byte and may link outside this skill.
    markdown = [skill_dir / 'SKILL.md', *skill_dir.glob('references/*.md'),
                *skill_dir.glob('assets/*.md'), *skill_dir.glob('evals/*.md')]
    for path in markdown:
        if not path.is_file():
            continue
        for target in LINK.findall(path.read_text(encoding='utf-8')):
            destination = target.split(' ', 1)[0].strip('<>')
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(skill_dir.resolve()) or not resolved.is_file():
                errors.append(f'Broken or outside-skill link in {path.relative_to(skill_dir)}: {destination}')
    return errors


def check_bump(current, base, changed):
    if not changed:
        return []
    try:
        current_version = version_tuple(current)
        if base is None:
            return [] if current_version == (1, 0, 0) else ['First tracked version must be 1.0.0.']
        if current_version <= version_tuple(base):
            return ['Skill changes require a SemVer version greater than the base version.']
    except ValueError as exc:
        return [str(exc)]
    return []


def git_comparison(base_ref, current_version):
    # CI checks committed changes relative to the target branch, not a local working tree.
    result = subprocess.run(['git', 'diff', '--name-only', base_ref, 'HEAD', '--', SKILL.name],
                            cwd=REPO, text=True, capture_output=True, check=False)
    if result.returncode:
        return ['Cannot compare against base ref; ensure its commit is available.']
    if not result.stdout.strip():
        return []
    before = subprocess.run(['git', 'show', f'{base_ref}:{SKILL.name}/SKILL.md'],
                            cwd=REPO, text=True, capture_output=True, check=False)
    if before.returncode:
        # Distinguish a genuinely new skill from an invalid/missing base reference.
        verified = subprocess.run(['git', 'rev-parse', '--verify', f'{base_ref}^{{commit}}'],
                                  cwd=REPO, text=True, capture_output=True, check=False)
        if verified.returncode:
            return ['Cannot resolve base ref.']
        return check_bump(current_version, None, True)
    try:
        meta = parse_frontmatter(before.stdout).get('metadata') or {}
        prior = meta.get('version') if isinstance(meta, dict) else None
        return check_bump(current_version, prior, True)
    except ValueError as exc:
        return [f'Cannot read base skill metadata: {exc}']


def validate(skill_dir=SKILL, base_ref=None):
    errors = []
    skill_file = skill_dir / 'SKILL.md'
    try:
        text = skill_file.read_text(encoding='utf-8')
        errors.extend(check_metadata(text, skill_dir.name))
        data = parse_frontmatter(text)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    errors.extend(check_relative_links(skill_dir))
    try:
        suite = json.loads((skill_dir / 'evals' / 'scenarios.json').read_text(encoding='utf-8'))
        errors.extend(check_scenarios(suite))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f'Cannot read evaluation suite: {exc}')
    if base_ref and not errors:
        if skill_dir.resolve() != SKILL.resolve():
            errors.append('Base comparison is only supported for the installed repository skill.')
        else:
            errors.extend(git_comparison(base_ref, data['metadata']['version']))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', help='Git base commit for the committed version-bump check.')
    args = parser.parse_args()
    errors = validate(base_ref=args.base_ref)
    result = {'ok': not errors, 'checks': ['frontmatter', 'version', 'relative-links', 'evaluation-suite'] + (['version-bump'] if args.base_ref else []), 'errors': errors}
    print(json.dumps(result, indent=2), file=sys.stderr if errors else sys.stdout)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
