#!/usr/bin/env python3
"""Archive browser-collected GitHub Explore summaries as JSON and Markdown."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def archive(data, root):
    status = data.get('status')
    if status not in {'complete', 'partial', 'blocked'}:
        raise ValueError('status must be complete, partial, or blocked')
    repos = data.get('repositories', [])
    if not isinstance(repos, list):
        raise ValueError('repositories must be a list')
    if status == 'complete' and (not repos or data.get('personalized') is not True):
        raise ValueError('complete requires verified personalized recommendations')
    if status != 'complete' and not data.get('notes'):
        raise ValueError('partial/blocked requires notes')
    seen = set()
    for repo in repos:
        name = repo.get('name', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name):
            raise ValueError('invalid repository name')
        if name.lower() in seen:
            raise ValueError('duplicate repository: ' + name)
        seen.add(name.lower())
        if repo.get('url') != 'https://github.com/' + name:
            raise ValueError('repository URL must match name')
        if not repo.get('summary'):
            raise ValueError('each repository requires a summary')
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    data = dict(data, archived_at=now.isoformat(), source='https://github.com/explore')
    folder = Path(root) / now.strftime('%Y-%m-%d') / now.strftime('%H%M%S-%f')
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [f'# GitHub Explore 日报 · {now:%Y-%m-%d}', '',
             f'状态：{status} ｜ 项目数：{len(repos)}', '',
             '[推荐来源](https://github.com/explore)', '', str(data.get('notes', '')), '']
    for i, repo in enumerate(repos, 1):
        lines += [f'## {i}. [{repo["name"]}]({repo["url"]})', '', repo['summary'], '']
        for key, label in [('use_cases', '适用场景'), ('highlights', '主要特点'),
                           ('language', '主要语言'), ('stars', 'Stars（采集时）'),
                           ('license', '许可证'), ('recommendation_reason', '页面推荐原因'),
                           ('read_status', '阅读状态')]:
            value = repo.get(key)
            if value is not None:
                lines += [f'- {label}：{value}']
        lines += ['']
    (folder / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSON produced from browser observations')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'reports')
    args = parser.parse_args()
    print(archive(json.loads(args.input.read_text(encoding='utf-8')), args.output))
