# Runbook

## Check current folder

Run:

```bash
pwd
```

Expected: path ends with `ux-rule-video-agent`.

## Activate environment

Run:

```bash
source .venv/bin/activate
```

Expected: terminal line starts with `(.venv)`.

## Check dependencies

Run:

```bash
python -c "import cv2, pandas, openpyxl, pydantic, PIL, imagehash, requests, dotenv, tqdm; print('зависимости установлены')"
```

Expected:

```text
зависимости установлены
```

## Check OpenRouter key

Run:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENROUTER_API_KEY найден' if os.getenv('OPENROUTER_API_KEY') and 'your_openrouter' not in os.getenv('OPENROUTER_API_KEY') else 'OPENROUTER_API_KEY не заполнен')"
```

Expected:

```text
OPENROUTER_API_KEY найден
```

Do not print the actual key.

## Check input files

Run:

```bash
test -f input/video.mp4 && echo "video.mp4 есть" || echo "video.mp4 нет"
```

Run:

```bash
test -f input/transcript.txt && echo "transcript.txt есть" || echo "transcript.txt нет"
```

## Run pipeline

Run:

```bash
python src/run_pipeline.py --video input/video.mp4 --transcript input/transcript.txt --config config.json
```

## Expected output

```text
output/reports/final_report.md
output/reports/ux_rule_creation_analysis.xlsx
```
