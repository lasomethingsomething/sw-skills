#!/usr/bin/env python3
"""Search bundled Shopware upgrade snapshots; return evidence candidates as JSON."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1] / 'references' / 'sources'
VERSION = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
RELEASE = re.compile(r'^#\s+(6\.\d+\.\d+\.\d+)(?:\s|$)')
HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')
TOKEN = re.compile(r'[\w\\.:-]+', re.UNICODE)


def version(value):
    if not VERSION.fullmatch(value):
        raise ValueError('Invalid Shopware version: expected four numeric parts.')
    return tuple(map(int, value.split('.')))


def selected_snapshots(current, target):
    source, dest = version(current), version(target)
    if not ((6, 6, 10, 0) <= source <= (6, 6, 10, 31)):
        raise ValueError('Bundled sources support current versions 6.6.10.0 through 6.6.10.31 only.')
    if not ((6, 7, 0, 0) <= dest <= (6, 7, 16, 0)):
        raise ValueError('Bundled sources support target versions 6.7.0.0 through 6.7.16.0 only.')
    src_ref = 'v6.6.10.0' if source == (6, 6, 10, 0) else 'v6.6.10.31'
    target_ref = 'v6.7.0.0' if dest == (6, 7, 0, 0) else 'v6.7.16.0'
    return source, dest, [('6.6', src_ref, ROOT / f'UPGRADE-6.6-{src_ref}.md'),
                          ('6.7', target_ref, ROOT / f'UPGRADE-6.7-{target_ref}.md')]


def sections(path):
    release = None
    fence = None
    section = None
    with path.open(encoding='utf-8') as f:
        for number, line in enumerate(f, 1):
            line = line.rstrip('\n')
            marker = FENCE.match(line)
            if marker:
                marker = marker.group(1)
                if fence is None:
                    fence = (marker[0], len(marker))
                elif marker[0] == fence[0] and len(marker) >= fence[1]:
                    fence = None
            if not fence and (h := HEADING.match(line)):
                if section:
                    yield section
                if m := RELEASE.match(line):
                    release = version(m.group(1))
                section = {'heading': h.group(2), 'line': number, 'release': release, 'lines': []}
            elif section is not None:
                section['lines'].append((number, line))
    if section:
        yield section


def search(current, target, query, limit=10, include_issues=False):
    source, dest, docs = selected_snapshots(current, target)
    terms = list(dict.fromkeys(TOKEN.findall(query.casefold())))
    if not terms:
        raise ValueError('The query must contain at least one searchable word or symbol.')
    hits = []
    for series, ref, path in docs:
        for s in sections(path):
            rel = s['release']
            if rel is None:
                continue
            # The 6.6 snapshot is announcement context, not a list of newly applied changes.
            if series == '6.7' and rel > dest:
                continue
            heading = s['heading'].casefold()
            body = '\n'.join(line for _, line in s['lines'])
            folded = body.casefold()
            score = sum(3 * heading.count(term) + min(folded.count(term), 4) for term in terms)
            if not score:
                continue
            relevant = [(n, line.strip()) for n, line in s['lines'] if any(t in line.casefold() for t in terms)]
            excerpts = [{'line': n, 'text': line[:450]} for n, line in relevant[:4]]
            hits.append({'score': score, 'source_series': series,
                         'release_heading': '.'.join(map(str, rel)),
                         'snapshot_ref': ref,
                         'exact_version_snapshot': (series == '6.6' and version(ref[1:]) == source) or (series == '6.7' and version(ref[1:]) == dest),
                         'heading': s['heading'], 'line': s['line'],
                         'url': f'https://github.com/shopware/shopware/blob/{ref}/UPGRADE-{series}.md#L{s["line"]}',
                         'local_file': f'references/sources/{path.name}', 'excerpts': excerpts})
    hits.sort(key=lambda h: (-h['score'], h['source_series'] != '6.7', h['line']))
    result = {'from_version': current, 'to_version': target,
              'notice': 'Candidates only. 6.6 is announcement context; later snapshots may revise earlier sections. Verify exact target tags, dates, status and applicability. A matching section is not proof of project impact.',
              'matches': hits[:limit]}
    if include_issues:
        index = json.loads((ROOT / 'github-issue-index.json').read_text(encoding='utf-8'))
        candidates = []
        for issue in index['issues']:
            title = issue['title'].casefold()
            score = sum(title.count(term) for term in terms)
            if score:
                candidates.append({'score': score, 'title': issue['title'], 'url': issue['url'],
                                   'source': 'curated public issue lead'})
        candidates.sort(key=lambda x: (-x['score'], x['url']))
        result['issue_notice'] = 'Unreviewed search leads, not confirmed changes or version-specific evidence. Inspect the live issue, comments and linked fixes.'
        result['issue_candidates'] = candidates[:limit]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-version', required=True)
    parser.add_argument('--to-version', required=True)
    query_input = parser.add_mutually_exclusive_group(required=True)
    query_input.add_argument('--query', help='Public, non-sensitive search terms; command arguments may be visible in process lists and shell history.')
    query_input.add_argument('--query-stdin', action='store_true', help='Read non-sensitive search terms from standard input instead of a command-line argument.')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--include-issues', action='store_true', help='Also search unreviewed issue titles.')
    args = parser.parse_args()
    try:
        if not 1 <= args.limit <= 100:
            raise ValueError('--limit must be between 1 and 100.')
        query = sys.stdin.read(4097) if args.query_stdin else args.query
        if len(query) > 4096:
            raise ValueError('Search query exceeds the 4096-character limit.')
        result = search(args.from_version, args.to_version, query, args.limit, args.include_issues)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
