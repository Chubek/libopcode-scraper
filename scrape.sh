#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  cat <<'EOF'
Usage:
  ./scrape.sh --arch <name> --format <json|yaml|xml|sexpr> [--output-dir <path>] [--scrape +all|+dis +opc|+inst]

Examples:
  ./scrape.sh --arch i386 --format json --scrape +all
  ./scrape.sh --arch aarch64 --format yaml --scrape +dis +opc
EOF
  exit 0
fi

if [ "$#" -eq 0 ]; then
  echo "error: no arguments provided" >&2
  echo "try: ./scrape.sh --help" >&2
  exit 2
fi

exec python3 -m Scrapers "$@"

