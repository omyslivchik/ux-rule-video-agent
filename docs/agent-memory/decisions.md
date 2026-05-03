# Project decisions

## 2026-05-01 — Focus on CJM, not workday snapshot

### Decision

The project analyzes only the scenario of creating rules on client operations.

It should not produce a general snapshot of the accountant workday.

### Why

The product question is:
- how does the accountant decide whether to create a rule;
- what checks are done;
- where risks and pains appear.

### Output sections

The final report must contain:
1. Краткое резюме
2. Слепок действий бухгалтера (хронологическая таблица)
3. CJM создания правила
4. Decision map
5. Наблюдаемые боли
6. Главный вывод

Do not include:
- separate automation opportunities section;
- separate quotes or video evidence section.

## 2026-05-03 — Слепок действий + скриншоты + цитаты в Excel

### Decision

The Excel report has two illustrated sheets:

**"Слепок действий"** — chronological table of all screen navigations:
- columns: Таймкод | Экран / интерфейс | Что делает бухгалтер | Вопрос или сложность | Реакция: куда идет дальше | Цитата | Скриншот
- one row per screen or meaningful action block
- shows returns and back-navigation as separate rows

**"CJM"** — strategic level (stages):
- columns: Этап | Таймкод | Что делает бухгалтер | Что пытается понять | Боль / риск | Цитата бухгалтера | Скриншот
- "Что делает бухгалтер" = numbered step list, minimum 2–4 specific steps

Screenshots are embedded using `openpyxl` Image, matched to nearest frame in `frames_kept/` by timecode.

### Why

The researcher needs to understand the full navigation flow, not just strategic stages.
Screen-by-screen view with quotes and screenshots makes it possible to see where difficulties arise and how the accountant reacts.
