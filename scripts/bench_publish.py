#!/usr/bin/env python3
"""Append a measurement to gh-pages, retrying optimistic Git publication races."""
import argparse
import subprocess
import time
from pathlib import Path

from bench_report import install, record_id


def git(repo, *args, check=True, input=None):
    return subprocess.run(['git', '-C', str(repo), '-c', 'user.name=bruster benchmarks',
                           '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com', *args],
                          input=input, text=True, capture_output=True, check=check)


def publish(repo, results, checkout, attempts=10):
    # An ephemeral worktree shares checkout's authentication without putting a
    # token in command arguments, or switching the measured source checkout.
    git(repo, 'worktree', 'add', '--detach', str(checkout), 'HEAD')
    try:
        for attempt in range(attempts):
            remote = git(repo, 'ls-remote', '--exit-code', 'origin', 'refs/heads/gh-pages', check=False)
            if remote.returncode == 0:
                git(repo, 'fetch', 'origin', '+refs/heads/gh-pages:refs/remotes/origin/gh-pages')
                base = 'refs/remotes/origin/gh-pages'
            elif remote.returncode == 2:
                tree = git(repo, 'mktree', input='').stdout.strip()
                base = git(repo, 'commit-tree', tree, '-m', 'Initialize benchmark site').stdout.strip()
            else:
                raise RuntimeError(remote.stderr)
            # Only this freshly created, disposable worktree is reset/cleaned.
            git(checkout, 'reset', '--hard', base)
            git(checkout, 'clean', '-fdx')
            record = install(results, checkout)
            git(checkout, 'add', 'benchmarks', '.nojekyll', 'index.html')
            if git(checkout, 'diff', '--cached', '--quiet', check=False).returncode == 0:
                return
            git(checkout, 'commit', '-m', f'benchmarks: {record_id(record)}')
            pushed = git(checkout, 'push', 'origin', 'HEAD:refs/heads/gh-pages', check=False)
            if pushed.returncode == 0:
                return
            # Re-read the branch and rebuild history rather than rebasing generated
            # indexes or force-pushing. All concurrent measurements survive.
            print(f'Publication attempt {attempt + 1} failed: {pushed.stderr}', flush=True)
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 30))
        raise RuntimeError('Unable to publish after retries; measurements remain in the workflow artifact')
    finally:
        git(repo, 'worktree', 'remove', '--force', str(checkout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--checkout', type=Path, required=True)
    args = parser.parse_args()
    publish(Path.cwd(), args.results.resolve(), args.checkout.resolve())


if __name__ == '__main__':
    main()
