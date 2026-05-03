# Bugs and fixes

## 2026-05-01 — Terminal commands got concatenated

### Symptom

The user ran two commands as one line:

`pip --versionpython -c "import cv2, pandas, openpyxl, pydantic, PIL, imagehash, requests, dotenv, tqdm; print('зависимости установлены')"`

The terminal returned:

```text
Usage:
  pip <command> [options]

no such option: --versionpython
```

### Root cause

Two separate commands were accidentally pasted without a line break:

```bash
pip --version
```

and:

```bash
python -c "import cv2, pandas, openpyxl, pydantic, PIL, imagehash, requests, dotenv, tqdm; print('зависимости установлены')"
```

Because there was no line break, the terminal interpreted this as one invalid command:

```bash
pip --versionpython
```

### Fix

Run the commands separately.

First run:

```bash
pip --version
```

Then run:

```bash
python -c "import cv2, pandas, openpyxl, pydantic, PIL, imagehash, requests, dotenv, tqdm; print('зависимости установлены')"
```

### Prevention rule for Cursor Agent

When giving terminal commands to the user, put each command on a separate line or in a separate block unless the commands are intentionally connected with `&&`.

Do not concatenate unrelated terminal commands in one line.

### Status

Resolved. The virtual environment was active, and the problem was caused by command formatting, not by Python or pip installation.

---

## 2026-05-01 — OPENROUTER_API_KEY was not filled

### Symptom

The project check returned:

```text
OPENROUTER_API_KEY не заполнен
```

### Root cause

The `.env` file existed, but the placeholder value was still present or the key was empty.

### Fix

Open `.env` and replace the placeholder with the real OpenRouter key.

Then check again with a safe command that does not print the key.

### Prevention rule for Cursor Agent

Never print the actual API key.

When checking `.env`, only verify that the key exists and is not a placeholder.

### Status

Resolved. The key was added to `.env` and the check passed.

---

## 2026-05-01 — User tried to use pwd to open a folder

### Symptom

The user tried to use `pwd` to open or enter the project folder.

### Root cause

`pwd` only shows the current directory. It does not open or change directories.

### Fix

Use:

```bash
pwd
```

to check the current folder.

Use:

```bash
ls
```

to see what is inside the current folder.

Use:

```bash
cd ux-rule-video-agent
```

to enter the project folder.

### Prevention rule for Cursor Agent

When explaining terminal navigation, always distinguish:

- `pwd` = show current folder
- `ls` = list files and folders
- `cd` = enter a folder

### Status

Resolved. The user entered the project folder and continued setup.

---

## 2026-05-03 — build_report filtered out interview scenes

### Symptom

Pipeline ran successfully through steps 1–3, but step 4 printed:

```text
Всего сцен: 1, используется: 0, пропущено: 1
Нет релевантных сцен для отчёта.
```

### Root cause

`build_report.py` filtered all scenes with `rule_creation_stage == "не относится к созданию правила"` via `SKIP_STAGES`.

When the video is an interview (not a screen recording of actual rule creation), `analyze_scenes` correctly labels the scene as "не относится к созданию правила" because no UI actions are visible. But the scene still contains rich content: decisions, risks, pains, and accountant reasoning.

### Fix

Added `_is_relevant()` function in `build_report.py`:
- If `rule_creation_stage` is not in `SKIP_STAGES` → include
- If it is in `SKIP_STAGES` but `decision`, `risk_or_pain`, or `short_summary` are non-empty → also include

### Prevention rule for Cursor Agent

Do not assume `rule_creation_stage = "не относится к созданию правила"` means the scene has no value.
Check whether `decision`, `risk_or_pain`, and `short_summary` fields have content before skipping.

### Status

Resolved. Report generated successfully after applying the fix.
