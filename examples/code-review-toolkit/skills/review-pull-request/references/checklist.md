# Full review checklist

## Correctness
- [ ] Edge cases: empty input, null, max sizes
- [ ] Error paths return/propagate correctly
- [ ] Concurrency: shared state guarded

## Security
- [ ] No secrets, tokens, or credentials in the diff
- [ ] User input validated before use in queries/commands/paths
- [ ] New dependencies come from trusted sources

## Tests
- [ ] New behavior covered by at least one test
- [ ] Tests fail if the feature is reverted

## Maintainability
- [ ] Public functions documented where non-obvious
- [ ] No copy-pasted blocks that should be shared
