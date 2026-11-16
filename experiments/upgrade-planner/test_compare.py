import copy
import json
from pathlib import Path
import tempfile
import unittest

import compare


class PairedExperimentTests(unittest.TestCase):
    def setUp(self):
        self.suite = json.loads(compare.SUITE.read_text(encoding='utf-8'))

    def test_prepared_case_starts_unscored_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'trial'
            compare.prepare(self.suite, 'admin-webpack', output, 7)
            assignment = json.loads((output / 'assignment.json').read_text())
            scorecard = json.loads((output / 'scorecard.json').read_text())
            summary = compare.summarize(assignment, scorecard, self.suite)
            self.assertEqual(summary['completed_pairs'], 0)
            self.assertTrue(all(v['pass'] == 0 and v['fail'] == 0 for v in summary['counts'].values()))
            self.assertEqual((output / 'prompt.txt').read_text().strip(), self.suite['scenarios'][0]['prompt'])
            with self.assertRaises(FileExistsError):
                compare.prepare(self.suite, 'admin-webpack', output, 7)

    def test_completed_pairs_only_and_condition_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'trial'
            compare.prepare(self.suite, 'admin-webpack', output, 23, 'previous')
            assignment = json.loads((output / 'assignment.json').read_text())
            scorecard = json.loads((output / 'scorecard.json').read_text())
            scorecard['criteria'][0]['A'] = 'pass'
            scorecard['criteria'][0]['B'] = 'fail'
            scorecard['criteria'][1]['A'] = 'pass'
            result = compare.summarize(assignment, scorecard, self.suite)
            self.assertEqual(result['completed_pairs'], 1)
            self.assertEqual(result['paired_results'][0][assignment['A']], 'pass')
            self.assertEqual(result['paired_results'][0][assignment['B']], 'fail')

    def test_rejects_wrong_scenario_altered_criteria_and_unknown_rating(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'trial'
            compare.prepare(self.suite, 'admin-webpack', output, 1)
            assignment = json.loads((output / 'assignment.json').read_text())
            scorecard = json.loads((output / 'scorecard.json').read_text())
            for mutation in ('scenario', 'text', 'rating'):
                bad = copy.deepcopy(scorecard)
                if mutation == 'scenario':
                    bad['scenario_id'] = 'unknown'
                elif mutation == 'text':
                    bad['criteria'][0]['criterion'] = 'changed'
                else:
                    bad['criteria'][0]['A'] = 'maybe'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    compare.summarize(assignment, bad, self.suite)


if __name__ == '__main__':
    unittest.main()
