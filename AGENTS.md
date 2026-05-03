# AGENTS.md

## Project goal

This project analyzes UX screen-recording videos where an accountant creates rules for client operations.

Input:
- `input/video.mp4`
- `input/transcript.txt`

Output:
- short summary
- CJM of rule creation
- decision map
- observed pains
- main conclusion

Do not produce a general snapshot of the accountant workday.
Focus only on the scenario of creating a rule.

## Required workflow for Cursor Agent

Before any task:
1. Read `.cursor/rules/ux-rule-video-agent.mdc`
2. Read `docs/agent-memory/decisions.md`
3. Read `docs/agent-memory/bugs_and_fixes.md`
4. Read `docs/agent-memory/lessons_learned.md`
5. Read `docs/agent-memory/runbook.md`
6. Read `docs/agent-memory/quality_checklist.md`
7. Read `docs/agent-memory/prompt_versions.md`

Then:
1. Restate the task briefly.
2. Propose a plan.
3. Do not change code until the user confirms.

After any task:
1. Summarize what changed.
2. Run relevant checks.
3. Propose memory updates if there were new bugs, decisions, or useful lessons.
4. Do not update memory silently without user confirmation.

## Run commands

Activate environment:

```bash
source .venv/bin/activate
```

Run full pipeline:

```bash
python src/run_pipeline.py --video input/video.mp4 --transcript input/transcript.txt --config config.json
```

Check output:

```bash
ls output/reports
```

Expected output:
- `output/reports/final_report.md`
- `output/reports/ux_rule_creation_analysis.xlsx`

## Safety

- Never print API keys.
- Never commit `.env`.
- Do not run destructive commands like `rm -rf` without explicit confirmation.
- Do not upload sensitive client data unless anonymized.
- If a command can delete or overwrite files, ask for confirmation first.
