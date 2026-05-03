"""
Точка входа пайплайна.

Полный запуск:
    python src/run_pipeline.py \
        --video input/video.mp4 \
        --transcript input/transcript.txt \
        --config config.json

Запуск отдельного шага:
    python src/run_pipeline.py --step extract  --video input/video.mp4 --config config.json
    python src/run_pipeline.py --step scenes   --config config.json
    python src/run_pipeline.py --step analyze  --transcript input/transcript.txt --config config.json
    python src/run_pipeline.py --step report   --config config.json
"""

import argparse
import json
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        print(f"[pipeline] config.json не найден: {config_path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(config_path.read_text(encoding="utf-8"))


def _check_env(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        print(
            "[pipeline] Файл .env не найден.\n"
            "  Скопируйте .env.example → .env и вставьте реальный OPENROUTER_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)
    if "your_openrouter_api_key_here" in env_path.read_text(encoding="utf-8"):
        print("[pipeline] OPENROUTER_API_KEY в .env не заменён.", file=sys.stderr)
        sys.exit(1)


def _check_file(path: Path, label: str) -> None:
    if not path.exists():
        print(f"[pipeline] Файл не найден ({label}): {path}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Шаги
# ---------------------------------------------------------------------------

def step_extract(args: argparse.Namespace, config: dict, project_root: Path) -> None:
    print("\n[pipeline] ── Шаг 1: extract_frames ──")
    t0 = time.time()
    from extract_frames import extract_frames
    video_path = (project_root / args.video).resolve() if args.video else project_root / "input" / "video.mp4"
    _check_file(video_path, "video")
    extract_frames(video_path, config, project_root)
    print(f"[pipeline] Шаг 1 завершён за {time.time() - t0:.1f}с")


def step_scenes(args: argparse.Namespace, config: dict, project_root: Path) -> None:
    print("\n[pipeline] ── Шаг 2: build_scenes ──")
    t0 = time.time()
    from build_scenes import run as build_scenes_run
    build_scenes_run(config, project_root)
    print(f"[pipeline] Шаг 2 завершён за {time.time() - t0:.1f}с")


def step_analyze(args: argparse.Namespace, config: dict, project_root: Path) -> None:
    print("\n[pipeline] ── Шаг 3: analyze_scenes ──")
    t0 = time.time()
    from analyze_scenes import run as analyze_run
    transcript_path = (
        (project_root / args.transcript).resolve()
        if args.transcript
        else project_root / "input" / "transcript.txt"
    )
    _check_file(transcript_path, "transcript")
    analyze_run(transcript_path, config, project_root)
    print(f"[pipeline] Шаг 3 завершён за {time.time() - t0:.1f}с")


def step_report(args: argparse.Namespace, config: dict, project_root: Path) -> None:
    print("\n[pipeline] ── Шаг 4: build_report ──")
    t0 = time.time()
    from build_report import run as report_run
    report_run(config, project_root)
    print(f"[pipeline] Шаг 4 завершён за {time.time() - t0:.1f}с")


STEPS = {
    "extract": step_extract,
    "scenes": step_scenes,
    "analyze": step_analyze,
    "report": step_report,
}
ALL_STEPS = ["extract", "scenes", "analyze", "report"]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="UX Rule Video Agent — анализ UX-видео",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            "  # Полный пайплайн:\n"
            "  python src/run_pipeline.py --video input/video.mp4 --transcript input/transcript.txt\n\n"
            "  # Только один шаг:\n"
            "  python src/run_pipeline.py --step analyze --transcript input/transcript.txt\n"
        ),
    )
    parser.add_argument("--video", default="input/video.mp4", help="Путь к видеофайлу")
    parser.add_argument("--transcript", default="input/transcript.txt", help="Путь к транскрипту")
    parser.add_argument("--config", default="config.json", help="Путь к config.json")
    parser.add_argument(
        "--step",
        choices=list(STEPS.keys()),
        default=None,
        help="Запустить только один шаг: extract | scenes | analyze | report",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    config_path = (project_root / args.config).resolve()
    config = _load_config(config_path)

    steps_to_run = [args.step] if args.step else ALL_STEPS

    if any(s in steps_to_run for s in ("analyze", "report")):
        _check_env(project_root)

    t_total = time.time()
    for step_name in steps_to_run:
        STEPS[step_name](args, config, project_root)

    elapsed = time.time() - t_total
    print(f"\n[pipeline] Готово. Общее время: {elapsed:.1f}с")
    print(f"[pipeline] Отчёты: {project_root / 'output' / 'reports'}")


if __name__ == "__main__":
    src_dir = Path(__file__).resolve().parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    main()
