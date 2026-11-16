import subprocess
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import search_sources as s


class SearchTests(unittest.TestCase):
    def test_target_zero_finds_payment_handler_in_exact_guide(self):
        result = s.search('6.6.10.0', '6.7.0.0', 'payment handler', 10)
        hit = next(x for x in result['matches'] if x['heading'] == 'Payment: Reworked payment handlers')
        self.assertTrue(hit['exact_version_snapshot'])
        self.assertEqual(hit['release_heading'], '6.7.0.0')
        self.assertEqual(hit['line'], 791)
        self.assertTrue(hit['url'].endswith('/v6.7.0.0/UPGRADE-6.7.md#L791'))

    def test_release_filter_does_not_report_later_minor(self):
        result = s.search('6.6.10.31', '6.7.14.0', 'document generation', 100)
        target_hits = [x for x in result['matches'] if x['source_series'] == '6.7']
        self.assertTrue(target_hits)
        self.assertTrue(all(s.version(x['release_heading']) <= s.version('6.7.14.0') for x in target_hits))
        self.assertTrue(all(x['snapshot_ref'] == 'v6.7.16.0' and not x['exact_version_snapshot'] for x in target_hits))

    def test_exact_latest_snapshot_is_labelled_correctly(self):
        result = s.search('6.6.10.31', '6.7.16.0', 'MCP allowlist', 10)
        hit = next(x for x in result['matches'] if 'allowlist' in x['heading'].lower())
        self.assertEqual(hit['release_heading'], '6.7.16.0')
        self.assertTrue(hit['exact_version_snapshot'])

    def test_rejects_unsupported_or_invalid_journeys(self):
        for start, target in [('6.5.0.0', '6.7.0.0'), ('6.6.10.32', '6.7.0.0'),
                              ('6.6.10.0', '6.7.17.0'), ('6.6', '6.7.0.0')]:
            with self.subTest(start=start, target=target):
                with self.assertRaises(ValueError):
                    s.search(start, target, 'upgrade')

    def test_issues_are_opt_in_and_unreviewed(self):
        plain = s.search('6.6.10.0', '6.7.0.0', 'upgrade', 10)
        self.assertNotIn('issue_candidates', plain)
        with_issues = s.search('6.6.10.0', '6.7.0.0', 'upgrade', 10, True)
        self.assertTrue(with_issues['issue_candidates'])
        self.assertIn('not confirmed', with_issues['issue_notice'])
        self.assertEqual(len(with_issues['issue_candidates']), 5)

    def test_query_and_absolute_local_paths_are_not_echoed(self):
        result = s.search('6.6.10.0', '6.7.0.0', 'payment handler', 10)
        self.assertNotIn('query', result)
        self.assertTrue(result['matches'])
        self.assertTrue(all(not Path(x['local_file']).is_absolute() for x in result['matches']))

    def test_stdin_query_is_not_echoed(self):
        command = [sys.executable, str(Path(s.__file__)), '--from-version', '6.6.10.0',
                   '--to-version', '6.7.0.0', '--query-stdin']
        result = subprocess.run(command, input='payment handler', capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('"query"', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_search_does_not_open_network_connections(self):
        with patch('socket.socket', side_effect=AssertionError('unexpected network access')):
            result = s.search('6.6.10.0', '6.7.0.0', 'payment', 5, True)
        self.assertTrue(result['matches'])

    def test_issue_index_contains_only_curated_minimal_fields(self):
        index = json.loads((s.ROOT / 'github-issue-index.json').read_text(encoding='utf-8'))
        self.assertEqual(len(index['issues']), 5)
        self.assertTrue(all(set(x) == {'title', 'url'} for x in index['issues']))

    def test_headings_inside_code_fences_do_not_change_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'guide.md'
            p.write_text('# 6.7.0.0\n## Example\n```markdown\n# 6.7.16.0\n```\n## After\ncontent\n')
            sections = list(s.sections(p))
        self.assertEqual([x['heading'] for x in sections], ['6.7.0.0', 'Example', 'After'])
        self.assertEqual(sections[-1]['release'], (6, 7, 0, 0))

    def test_json_command_fails_for_unsupported_version(self):
        command = [sys.executable, str(Path(s.__file__)), '--from-version', '6.6.10.0',
                   '--to-version', '6.8.0.0', '--query', 'payment']
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn('target versions', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
