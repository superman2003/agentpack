---
description: Fast review of uncommitted changes. Invoke with /quick-review.
---

Review the current uncommitted changes (`git diff` plus untracked files):

1. Run `git status` and `git diff` to collect the changes.
2. Apply the review-pull-request skill checklist, but only report blocking issues.
3. Finish with a one-line verdict: safe to commit, or not.
