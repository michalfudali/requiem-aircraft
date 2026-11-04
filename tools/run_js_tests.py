"""Run every Node test file, on Windows and Linux, with a machine-readable report."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--junit', type=Path, default=ROOT / 'work/javascript.xml')
    args = parser.parse_args()
    if not args.node:
        parser.error('Node.js is required; install Node or pass --node /path/to/node')
    files = sorted((ROOT / 'tests').glob('*.test.mjs'))
    if not files:
        parser.error('No JavaScript tests found')
    args.junit.parent.mkdir(parents=True, exist_ok=True)
    print(f'Running all {len(files)} JavaScript test files', flush=True)
    return subprocess.run([args.node, '--test', '--test-reporter=spec', '--test-reporter=junit',
        '--test-reporter-destination=stdout', f'--test-reporter-destination={args.junit.resolve()}',
        *map(str, files)], cwd=ROOT).returncode


if __name__ == '__main__':
    sys.exit(main())
