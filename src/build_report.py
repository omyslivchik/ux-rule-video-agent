"""
Шаг 4. Строит итоговый отчёт из output/chunks/scene_analyses.jsonl.

- Читает все записи из scene_analyses.jsonl
- Отбирает сцены, связанные с созданием правила
- Один запрос к OpenRouter → получает Markdown-отчёт
- Парсит из Markdown таблицы (CJM, Decision Map, Боли)
- Сохраняет:
  - output/reports/final_report.md
  - output/reports/ux_rule_creation_analysis.xlsx   (листы: Summary, CJM, Decision Map, Pains)
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

SKIP_STAGES = {"не относится к созданию правила"}


# ---------------------------------------------------------------------------
# Запрос к OpenRouter (текст)
# ---------------------------------------------------------------------------

def _call_openrouter_text(prompt: str, env: dict, config: dict) -> str:
    headers = {
        "Authorization": f"Bearer {env['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": env.get("OPENROUTER_HTTP_REFERER", ""),
        "X-Title": env.get("OPENROUTER_X_TITLE", ""),
    }
    payload = {
        "model": env["OPENROUTER_MODEL"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config["openrouter_temperature"],
        "max_tokens": config["openrouter_max_tokens"],
    }

    max_retries: int = config["max_retries"]
    backoff: float = config["retry_backoff_sec"]
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                env["OPENROUTER_BASE_URL"],
                headers=headers,
                json=payload,
                timeout=config["request_timeout_sec"],
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError) as e:
            last_err = e
            wait = backoff * (2 ** (attempt - 1))
            print(
                f"[build_report] Ошибка попытка {attempt}/{max_retries}: {e}. Жду {wait:.1f}с...",
                file=sys.stderr,
            )
            time.sleep(wait)

    raise RuntimeError(f"[build_report] Не удалось получить отчёт: {last_err}")


# ---------------------------------------------------------------------------
# Парсинг Markdown-таблиц
# ---------------------------------------------------------------------------

def _parse_md_table(md_text: str, section_keyword: str) -> pd.DataFrame:
    """
    Находит первую Markdown-таблицу после строки, содержащей section_keyword.
    """
    lines = md_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if section_keyword.lower() in line.lower():
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped.startswith("|"):
                    start = j
                    break
            if start is not None:
                break

    if start is None:
        return pd.DataFrame()

    table_lines = []
    for line in lines[start:]:
        if not line.strip().startswith("|"):
            break
        table_lines.append(line.strip())

    if len(table_lines) < 2:
        return pd.DataFrame()

    def split_row(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    headers = split_row(table_lines[0])
    rows = []
    for line in table_lines[2:]:
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        rows.append(split_row(line))

    return pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame(columns=headers)


def _extract_summary_text(md_text: str) -> str:
    """Извлекает текст раздела '1. Краткое резюме'."""
    match = re.search(
        r"##\s*1\.\s*Краткое резюме\s*(.*?)(?=##\s*2\.|$)",
        md_text,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else md_text[:500]


# ---------------------------------------------------------------------------
# Запись Excel
# ---------------------------------------------------------------------------

def _write_excel(report_md: str, chunks: list[dict], out_path: Path) -> None:
    cjm_df = _parse_md_table(report_md, "CJM")
    decision_df = _parse_md_table(report_md, "Decision Map")
    if decision_df.empty:
        decision_df = _parse_md_table(report_md, "Decision map")
    pains_df = _parse_md_table(report_md, "Наблюдаемые боли")
    if pains_df.empty:
        pains_df = _parse_md_table(report_md, "Pains")

    summary_text = _extract_summary_text(report_md)
    summary_df = pd.DataFrame([{
        "Параметр": "Краткое резюме",
        "Значение": summary_text,
    }, {
        "Параметр": "Всего сцен проанализировано",
        "Значение": len(chunks),
    }, {
        "Параметр": "Сцен с ошибками",
        "Значение": sum(1 for c in chunks if "error" in c),
    }])

    with pd.ExcelWriter(str(out_path), engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        if not cjm_df.empty:
            cjm_df.to_excel(writer, sheet_name="CJM", index=False)
        else:
            pd.DataFrame(columns=["Нет данных"]).to_excel(writer, sheet_name="CJM", index=False)
        if not decision_df.empty:
            decision_df.to_excel(writer, sheet_name="Decision Map", index=False)
        else:
            pd.DataFrame(columns=["Нет данных"]).to_excel(writer, sheet_name="Decision Map", index=False)
        if not pains_df.empty:
            pains_df.to_excel(writer, sheet_name="Pains", index=False)
        else:
            pd.DataFrame(columns=["Нет данных"]).to_excel(writer, sheet_name="Pains", index=False)

    print(f"[build_report] Excel сохранён → {out_path}")


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def run(config: dict, project_root: Path) -> None:
    load_dotenv(project_root / ".env")

    env = {
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "OPENROUTER_MODEL": os.environ.get("OPENROUTER_MODEL", ""),
        "OPENROUTER_BASE_URL": os.environ.get("OPENROUTER_BASE_URL", ""),
        "OPENROUTER_HTTP_REFERER": os.environ.get("OPENROUTER_HTTP_REFERER", ""),
        "OPENROUTER_X_TITLE": os.environ.get("OPENROUTER_X_TITLE", ""),
    }

    if not env["OPENROUTER_API_KEY"] or env["OPENROUTER_API_KEY"].startswith("your_"):
        print("[build_report] OPENROUTER_API_KEY не задан в .env", file=sys.stderr)
        sys.exit(1)

    analyses_path = project_root / "output" / "chunks" / "scene_analyses.jsonl"
    if not analyses_path.exists():
        print(f"[build_report] Не найден {analyses_path}. Сначала запустите analyze_scenes.", file=sys.stderr)
        sys.exit(1)

    all_chunks = [
        json.loads(line)
        for line in analyses_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    relevant_chunks = [
        c for c in all_chunks
        if c.get("rule_creation_stage", "") not in SKIP_STAGES
    ]

    skipped = len(all_chunks) - len(relevant_chunks)
    print(f"[build_report] Всего сцен: {len(all_chunks)}, используется: {len(relevant_chunks)}, пропущено: {skipped}")

    if not relevant_chunks:
        print("[build_report] Нет релевантных сцен для отчёта.", file=sys.stderr)
        sys.exit(1)

    prompt_template = (project_root / "prompts" / "final_report_prompt.md").read_text(encoding="utf-8")
    chunks_json = json.dumps(relevant_chunks, ensure_ascii=False, indent=2)
    final_prompt = f"{prompt_template}\n\n---\n\n## Данные сцен:\n\n```json\n{chunks_json}\n```"

    print("[build_report] Отправляю запрос в OpenRouter...")
    report_md = _call_openrouter_text(final_prompt, env, config)

    reports_dir = project_root / "output" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    md_path = reports_dir / "final_report.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"[build_report] Markdown → {md_path}")

    xlsx_path = reports_dir / "ux_rule_creation_analysis.xlsx"
    _write_excel(report_md, all_chunks, xlsx_path)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
    run(cfg, root)
