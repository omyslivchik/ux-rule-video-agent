# Lessons learned

## 2026-05-01 — Keep the final report short

The user prefers a compact management-style report.

The final report should contain only:

1. Краткое резюме
2. CJM создания правила
3. Decision map
4. Наблюдаемые боли
5. Главный вывод

Do not add separate sections:

- Возможности автоматизации
- Цитаты и видео-доказательства

Reason:

The user wants a short product/management document, not a long research repository output.

---

## 2026-05-01 — Focus on rule creation, not workday snapshot

The project should not produce a general snapshot of the accountant workday.

The real product question is:

How does the accountant decide whether to create a rule, what checks do they perform, where do risks and pains appear?

The analysis should focus on the scenario:

1. Finds a candidate operation
2. Checks repeatability
3. Reviews similar operations
4. Assesses risk
5. Sets rule conditions
6. Saves the rule
7. Checks the result

Reason:

A workday snapshot answers what happened on screen.

The project needs to answer how the accountant makes a safe decision when creating a rule.

---

## 2026-05-01 — Analyze decisions, not only clicks

The agent should not only describe UI actions like:

- opened list
- applied filter
- selected row
- clicked button

The agent should also extract the decision logic:

- why this operation looked like a candidate for a rule
- what evidence of repeatability was checked
- why the rule condition was narrow or broad
- what risk the accountant was trying to avoid
- how the accountant checked the result

Reason:

The value of the analysis is in reconstructing accountant judgment, not in creating a click log.

---

## 2026-05-01 — Use project memory as the source of truth

Cursor should not rely only on chat memory.

Before working on the project, the agent should read:

- `AGENTS.md`
- `.cursor/rules/ux-rule-video-agent.mdc`
- `docs/agent-memory/decisions.md`
- `docs/agent-memory/bugs_and_fixes.md`
- `docs/agent-memory/lessons_learned.md`
- `docs/agent-memory/runbook.md`
- `docs/agent-memory/quality_checklist.md`
- `docs/agent-memory/prompt_versions.md`

Reason:

Project memory makes the agent behavior consistent across sessions and helps avoid repeating the same mistakes.

---

## 2026-05-01 — Prefer safe step-by-step terminal instructions

The user is learning terminal and GitHub workflows.

When giving terminal instructions, the agent should:

- explain what the command does;
- give one command at a time;
- avoid long combined commands unless necessary;
- warn before destructive commands;
- verify results after each important step.

Reason:

This reduces confusion and prevents accidental errors during setup.

---

## 2026-05-03 — Interview videos produce valid output even without UI actions

The pipeline works on interview-format videos where the accountant describes their process verbally, not screen recordings of actual rule creation.

In this case:
- `analyze_scenes` will label the scene as "не относится к созданию правила" because no UI actions are visible
- But `decision`, `risk_or_pain`, `short_summary` fields will be filled with rich content from the transcript
- `build_report` must not skip these scenes

The final report should note that data comes from an interview, not observed behavior.
The model does this automatically when given the right context.

Reason:

Interview sessions capture accountant reasoning, decision logic, and fears — which are exactly what the project needs. They are valid input even without screen interaction.
