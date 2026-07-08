---
name: review-pull-request
description: Use when asked to review a pull request, diff, or branch changes. Provides a methodical review checklist covering correctness, security, and maintainability.
---

# Review a pull request

Review changes in this order, and report findings grouped by severity.

## Instructions

1. Read the full diff before commenting on anything.
2. Check correctness first: logic errors, off-by-one, unhandled error paths, race conditions.
3. Check security: injection, secrets in code, unsafe deserialization, missing input validation.
4. Check tests: does new behavior have coverage? Do the tests assert outcomes, not implementation?
5. Check maintainability last: naming, duplication, dead code.
6. See `references/checklist.md` for the full item-by-item checklist.

## Reporting

- Group findings as: blocking, should-fix, nit.
- Quote the exact file and line for every finding.
- If the change looks good, say so plainly; do not invent nits.
