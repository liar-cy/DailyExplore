#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

input=${1:-staging/current.json}
archive_dir=$(python3 scripts/archive.py "$input")

git add "$archive_dir/data.json" "$archive_dir/report.md"
if git diff --cached --quiet; then
  echo "No new report to publish"
  exit 0
fi

report_date=$(basename "$(dirname "$archive_dir")")
git commit -m "docs: add GitHub Explore report for $report_date"
git push origin HEAD:main
echo "Published $archive_dir"
