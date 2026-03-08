# SOUL.md Notes

The live OpenClaw workspace contains a `SOUL.md` file under `~/.openclaw/workspace/`.

## Verified high-level content

- It defines the assistant's tone and behavioral boundaries.
- It emphasizes being resourceful before asking questions.
- It includes privacy and external-action safety guidance.
- It acts as a persistent identity/behavior file for the live OpenClaw runtime.

## Rebuild implication

The future monorepo should treat `SOUL.md`-style runtime identity and behavior files as first-class external runtime artifacts, with sanitized templates or policy notes stored in-repo.
