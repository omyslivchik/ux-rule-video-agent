# Project memory setup

This archive contains ready-to-use project memory files for the `ux-rule-video-agent` Cursor project.

## How to use

1. Unzip the archive.
2. Copy all files and folders into the root of your Cursor project:
   `ux-rule-video-agent/`
3. If Cursor asks whether to merge folders, choose merge.
4. Do not overwrite existing files blindly if you already edited them manually.

## Files included

- `AGENTS.md`
- `.cursor/rules/ux-rule-video-agent.mdc`
- `.cursor/plans/`
- `docs/agent-memory/decisions.md`
- `docs/agent-memory/bugs_and_fixes.md`
- `docs/agent-memory/lessons_learned.md`
- `docs/agent-memory/runbook.md`
- `docs/agent-memory/quality_checklist.md`
- `docs/agent-memory/prompt_versions.md`
- `.gitignore`

## Verification command

From the project root, run:

```bash
test -f AGENTS.md && echo "AGENTS.md exists"
test -f .cursor/rules/ux-rule-video-agent.mdc && echo "Cursor rule exists"
test -f docs/agent-memory/decisions.md && echo "decisions.md exists"
test -f docs/agent-memory/bugs_and_fixes.md && echo "bugs_and_fixes.md exists"
test -f docs/agent-memory/lessons_learned.md && echo "lessons_learned.md exists"
test -f docs/agent-memory/runbook.md && echo "runbook.md exists"
test -f docs/agent-memory/quality_checklist.md && echo "quality_checklist.md exists"
test -f docs/agent-memory/prompt_versions.md && echo "prompt_versions.md exists"
```

## Prompt for Cursor Agent after copying

Read `AGENTS.md` and the files in `docs/agent-memory/`.
Check that project memory is installed correctly.
Do not run the pipeline and do not change Python code.
