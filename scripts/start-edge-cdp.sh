#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
profile_dir="$project_dir/.edge-cdp-profile"
mkdir -p "$profile_dir"
chmod 700 "$profile_dir"
open -na "Microsoft Edge" --args \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="$profile_dir" \
  https://github.com/explore
