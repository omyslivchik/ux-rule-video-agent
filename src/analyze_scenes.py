"""
Шаг 3. Анализирует каждую сцену через OpenRouter Vision API.

Читает:
- output/scenes.jsonl           — список сцен из build_scenes
- input/transcript.txt          — расшифровка разговора
- prompts/scene_analysis_prompt.md

Для каждой сцены:
- вырезает фрагмент транскрипта по таймкодам;
- кодирует кадры в base64;
- добавляет short_summary предыдущей сцены как контекст;
- отправляет multimodal-запрос в OpenRouter;
- парсит JSON-ответ;
- дописывает строку в output/chunks/scene_analyses.jsonl.

При ошибке сети или парсинга — записывает запись с флагом error, не останавливает пайплайн.
"""

import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Транскрипт
# ---------------------------------------------------------------------------

def _parse_transcript(path: Path) -> list[dict]:
    """
    Форматы:
      [HH:MM:SS] текст
      [MM:SS] текст
      Простой текст → один блок, start_sec=0
    """
    if not path.exists():
        print(f"[analyze_scenes] Транскрипт не найден: {path}. Будет использован пустой контекст.")
        return []

    raw = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*(.*?)(?=\[\d|$)",
        re.DOTALL,
    )
    matches = list(pattern.finditer(raw))
    if not matches:
        return [{"start_sec": 0.0, "text": raw.strip()}]

    result = []
    for m in matches:
        if m.group(3) is not None:
            h, mm, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
            start = h * 3600 + mm * 60 + s
        else:
            mm, s = int(m.group(1)), int(m.group(2))
            start = mm * 60 + s
        text = m.group(4).strip()
        if text:
            result.append({"start_sec": float(start), "text": text})
    return result


def _get_transcript_chunk(
    transcript: list[dict],
    start_sec: float,
    end_sec: float,
    padding_sec: float = 5.0,
) -> str:
    lo = max(0.0, start_sec - padding_sec)
    hi = end_sec + padding_sec
    parts = [t["text"] for t in transcript if lo <= t["start_sec"] <= hi]
    return " ".join(parts).strip() or "транскрипт отсутствует"


# ---------------------------------------------------------------------------
# Запрос к OpenRouter
# ---------------------------------------------------------------------------

def _encode_image(path: str) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_content(
    prompt_text: str,
    scene: dict,
    transcript_chunk: str,
    prev_summary: str,
    max_prev_chars: int,
) -> list:
    context = ""
    if prev_summary:
        context = f"\n\n**Контекст предыдущей сцены:**\n{prev_summary[:max_prev_chars]}"

    text = (
        f"{prompt_text}"
        f"{context}\n\n"
        f"**Сцена:** {scene['scene_id']}\n"
        f"**Таймкод:** {scene['start_sec']}–{scene['end_sec']} сек\n\n"
        f"**Транскрипт фрагмента:**\n{transcript_chunk}"
    )

    content: list = [{"type": "text", "text": text}]
    for fp in scene.get("frame_paths", []):
        b64 = _encode_image(fp)
        if b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
    return content


def _call_openrouter(messages: list, env: dict, config: dict) -> str:
    headers = {
        "Authorization": f"Bearer {env['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": env.get("OPENROUTER_HTTP_REFERER", ""),
        "X-Title": env.get("OPENROUTER_X_TITLE", ""),
    }
    payload = {
        "model": env["OPENROUTER_MODEL"],
        "messages": messages,
        "temperature": config["openrouter_temperature"],
        "max_tokens": config["openrouter_max_tokens"],
    }
    resp = requests.post(
        env["OPENROUTER_BASE_URL"],
        headers=headers,
        json=payload,
        timeout=config["request_timeout_sec"],
    )
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    finish_reason = choice.get("finish_reason", "unknown")
    content = choice["message"].get("content") or ""
    if not content.strip():
        # Log full response for diagnosis
        usage = data.get("usage", {})
        print(
            f"[analyze_scenes] WARN: пустой ответ. finish_reason={finish_reason!r}, "
            f"usage={usage}, raw_choice={json.dumps(choice, ensure_ascii=False)[:500]}",
            file=sys.stderr,
        )
        raise ValueError(f"Пустой ответ от модели (finish_reason={finish_reason!r})")
    return content


def _extract_json(text: str) -> dict:
    # Greedy match to capture the full JSON object inside code fences
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Fallback: find any JSON object greedily
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"JSON не найден в ответе: {text[:300]}")


def analyze_one_scene(
    scene: dict,
    transcript_chunk: str,
    prev_summary: str,
    prompt_text: str,
    env: dict,
    config: dict,
) -> dict:
    max_retries: int = config["max_retries"]
    backoff: float = config["retry_backoff_sec"]
    max_prev_chars: int = config["max_previous_summary_chars"]

    content = _build_content(prompt_text, scene, transcript_chunk, prev_summary, max_prev_chars)
    messages = [{"role": "user", "content": content}]

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = _call_openrouter(messages, env, config)
            result = _extract_json(raw)
            result.setdefault("scene_id", scene["scene_id"])
            result.setdefault("start_sec", scene["start_sec"])
            result.setdefault("end_sec", scene["end_sec"])
            return result
        except (requests.RequestException, ValueError, KeyError) as e:
            last_err = e
            wait = backoff * (2 ** (attempt - 1))
            print(
                f"[analyze_scenes] {scene['scene_id']} — ошибка попытка {attempt}/{max_retries}: {e}. "
                f"Жду {wait:.1f}с...",
                file=sys.stderr,
            )
            time.sleep(wait)

    print(
        f"[analyze_scenes] {scene['scene_id']} — не удалось после {max_retries} попыток.",
        file=sys.stderr,
    )
    return {
        "scene_id": scene["scene_id"],
        "start_sec": scene["start_sec"],
        "end_sec": scene["end_sec"],
        "rule_creation_stage": "непонятно",
        "short_summary": "",
        "error": str(last_err),
    }


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def run(transcript_path: Path, config: dict, project_root: Path) -> list[dict]:
    load_dotenv(project_root / ".env")

    env = {
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "OPENROUTER_MODEL": os.environ.get("OPENROUTER_MODEL", ""),
        "OPENROUTER_BASE_URL": os.environ.get("OPENROUTER_BASE_URL", ""),
        "OPENROUTER_HTTP_REFERER": os.environ.get("OPENROUTER_HTTP_REFERER", ""),
        "OPENROUTER_X_TITLE": os.environ.get("OPENROUTER_X_TITLE", ""),
    }

    if not env["OPENROUTER_API_KEY"] or env["OPENROUTER_API_KEY"].startswith("your_"):
        print("[analyze_scenes] OPENROUTER_API_KEY не задан в .env", file=sys.stderr)
        sys.exit(1)

    scenes_jsonl = project_root / "output" / "scenes.jsonl"
    if not scenes_jsonl.exists():
        print(f"[analyze_scenes] Не найден {scenes_jsonl}. Сначала запустите build_scenes.", file=sys.stderr)
        sys.exit(1)

    scenes = [json.loads(line) for line in scenes_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not scenes:
        print("[analyze_scenes] scenes.jsonl пустой.", file=sys.stderr)
        sys.exit(1)

    transcript = _parse_transcript(transcript_path)
    prompt_text = (project_root / "prompts" / "scene_analysis_prompt.md").read_text(encoding="utf-8")

    chunks_dir = project_root / "output" / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    out_path = chunks_dir / "scene_analyses.jsonl"

    results: list[dict] = []
    prev_summary = ""
    errors = 0

    with open(out_path, "w", encoding="utf-8") as out_file:
        for scene in tqdm(scenes, desc="analyze_scenes", unit="scene"):
            transcript_chunk = _get_transcript_chunk(
                transcript, scene["start_sec"], scene["end_sec"]
            )
            result = analyze_one_scene(
                scene, transcript_chunk, prev_summary, prompt_text, env, config
            )
            if "error" in result:
                errors += 1
            prev_summary = result.get("short_summary", "")
            out_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            results.append(result)

    print(f"[analyze_scenes] Обработано {len(results)} сцен, ошибок: {errors} → {out_path}")
    return results


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
    run(root / "input" / "transcript.txt", cfg, root)
