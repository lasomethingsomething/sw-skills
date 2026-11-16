"""Tests for the upgrade planner's lifecycle checks."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import check_skill


class MetadataTests(unittest.TestCase):
    def test_real_skill_metadata_is_valid(self):
        self.assertEqual([], check_skill.check_metadata(
            (check_skill.SKILL / 'SKILL.md').read_text(), check_skill.SKILL.name))

    def test_rejects_wrong_name_missing_description_and_invalid_version(self):
        text = '---\nname: wrong\ndescription: ""\nmetadata:\n  version: "1.2"\n---\n'
        errors = check_skill.check_metadata(text, 'shopware-upgrade-planner')
        self.assertEqual(3, len(errors))

    def test_rejects_non_string_metadata(self):
        text = '---\nname: sample\ndescription: Sample\nmetadata:\n  version: 1.0\n---\n'
        self.assertTrue(check_skill.check_metadata(text, 'sample'))


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.suite = json.loads((check_skill.SKILL / 'evals/scenarios.json').read_text())

    def test_repository_scenarios_are_valid(self):
        self.assertEqual([], check_skill.check_scenarios(self.suite))

    def test_duplicate_scenario_prompt_and_criterion_are_rejected(self):
        bad = copy.deepcopy(self.suite)
        bad['scenarios'].append(copy.deepcopy(bad['scenarios'][0]))
        errors = check_skill.check_scenarios(bad)
        self.assertTrue(any('Scenario IDs' in error for error in errors))
        self.assertTrue(any('prompts' in error for error in errors))
        self.assertTrue(any('Criterion IDs' in error for error in errors))

    def test_extra_criterion_field_is_rejected(self):
        self.suite['scenarios'][0]['criteria'][0]['extra'] = True
        self.assertTrue(check_skill.check_scenarios(self.suite))


class LinkTests(unittest.TestCase):
    def test_local_links_are_checked_and_external_links_are_not_fetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / 'skill'
            (skill / 'references').mkdir(parents=True)
            (skill / 'references' / 'good.md').write_text('ok')
            (skill / 'SKILL.md').write_text(
                '[good](references/good.md#section) [missing](references/missing.md) '
                '[outside](../secret.md) [web](https://example.invalid/a)')
            errors = check_skill.check_relative_links(skill)
            self.assertEqual(2, len(errors))
            self.assertTrue(any('missing.md' in error for error in errors))
            self.assertTrue(any('secret.md' in error for error in errors))


class VersionTests(unittest.TestCase):
    def test_bump_rules(self):
        self.assertEqual([], check_skill.check_bump('1.0.0', None, True))
        self.assertTrue(check_skill.check_bump('1.0.0', '1.0.0', True))
        self.assertEqual([], check_skill.check_bump('1.0.1', '1.0.0', True))
        self.assertEqual([], check_skill.check_bump('1.0.0', '1.0.0', False))
        self.assertTrue(check_skill.check_bump('0.1.0', None, True))

    def test_git_comparison_requires_bump_on_committed_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            skill = repo / 'planner'
            skill.mkdir()
            path = skill / 'SKILL.md'
            path.write_text('---\nname: planner\ndescription: Sample\nmetadata:\n  version: "1.0.0"\n---\n')
            def commit(message):
                subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
                subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                'commit', '-q', '-m', message], cwd=repo, check=True)
            commit('base')
            base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
            (skill / 'extra.md').write_text('change')
            commit('change')
            with patch.object(check_skill, 'REPO', repo), patch.object(check_skill, 'SKILL', skill):
                self.assertTrue(check_skill.git_comparison(base, '1.0.0'))
                self.assertEqual([], check_skill.git_comparison(base, '1.0.1'))
                self.assertTrue(check_skill.git_comparison('missing-ref', '1.0.1'))


if __name__ == '__main__':
    unittest.main()
