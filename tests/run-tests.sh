#!/usr/bin/env bash
# Single entry point for every test in the repo. Fails on the first error.
#   1. raco test racket/            (Racket unit tests of the port)
#   2. chez_scheme/oracle/tests/*.ss (Chez oracle checks, each run with `scheme --script`;
#                                    a check fails by exiting non-zero)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

SCHEME="$(command -v scheme || command -v chezscheme || true)"
if [ -z "$SCHEME" ]; then
  echo "run-tests: Chez Scheme not found (sudo apt install chezscheme)" >&2
  exit 1
fi

echo "== raco test racket/"
raco test racket/

echo "== Chez oracle checks"
shopt -s nullglob
checks=(chez_scheme/oracle/tests/*.ss)
if [ ${#checks[@]} -eq 0 ]; then
  echo "run-tests: no Chez checks found in chez_scheme/oracle/tests/" >&2
  exit 1
fi
for t in "${checks[@]}"; do
  echo "-- $t"
  "$SCHEME" --script "$t"
done

echo "== all tests passed"
