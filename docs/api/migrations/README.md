# API migrations

This directory holds consumer instructions for API contract changes. The
current contract is v1 and has no breaking predecessor, so no client migration
is required at publication time.

For every future breaking change, add `v1-to-v2.md` (using the real version
numbers) with these sections:

1. Summary and reason
2. Affected consumers and contracts
3. Before and after examples
4. Client migration steps
5. Compatibility window and cutover
6. Rollback
7. Verification performed

The migration guide and new versioned examples must land with the breaking
code change, not in a later cleanup pull request.
