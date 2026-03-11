# Next Steps

Updated: 2026-03-10

## Decision From Tonight

- Do not set up OpenClaw command behavior as a chat-defined persistent session.
- Keep command logic in the repo and let OpenClaw call repo-managed wrappers.
- Treat the deployed OpenClaw environment as runtime state, not as the source of truth.

## 1. Pull Approved OpenClaw Environment Changes Back Into The Repo

- Define which parts of the deployed OpenClaw home are allowed to drift and which must remain repo-managed.
- Add a controlled sync flow from the deployed environment back into the repository for approved changes.
- Include safeguards so runtime-only state, secrets, logs, and session artifacts are never pulled into git.
- Decide on the review path for environment-originated changes before they are committed.

## Remaining Focus

1. Decide whether environment-originated OpenClaw changes should ever flow back into the repo, or whether the repo-to-runtime sync should remain strictly one-way.
2. If reverse sync is allowed, define an explicit allowlist and review path before implementing it.

## Additional Tasks

1. Manage OpenClaw memory/context.
2. Update OpenClaw.