"""
Шаг 1. Нарезает видео на JPEG-кадры с заданной частотой.

Сохраняет:
- output/frames_raw/frame_XXXXXXXXXX.jpg  (имя = timestamp в мс)
- output/frames_index.jsonl               (одна JSON-запись на каждый кадр)
"""

import json
import sys
from pathlib import Path

import cv2
from tqdm import tqdm


def extract_frames(video_path: Path, config: dict, project_root: Path, session_dir: Path = None) -> None:
    if session_dir is None:
        session_dir = project_root / "output"
    out_dir = session_dir / "frames_raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_fps: float = config["sample_fps"]
    jpeg_quality: int = config["jpeg_quality"]
    resize_width: int = config["resize_width"]

    if not video_path.exists():
        print(f"[extract_frames] Видео не найдено: {video_path}", file=sys.stderr)
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[extract_frames] Не удалось открыть видео: {video_path}", file=sys.stderr)
        sys.exit(1)

    source_fps: float = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec: float = total_frames / source_fps
    frame_interval: int = max(1, round(source_fps / sample_fps))

    print(
        f"[extract_frames] Видео: {total_frames} кадров, {source_fps:.1f} fps, "
        f"~{duration_sec:.1f} сек. Интервал выборки: каждый {frame_interval}-й кадр."
    )

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    index_path = session_dir / "frames_index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    saved = 0
    frame_idx = 0

    with (
        tqdm(total=total_frames, desc="extract_frames", unit="frame") as pbar,
        open(index_path, "w", encoding="utf-8") as index_file,
    ):
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))

                orig_w, orig_h = frame.shape[1], frame.shape[0]
                if resize_width and orig_w > resize_width:
                    scale = resize_width / orig_w
                    new_h = int(orig_h * scale)
                    frame = cv2.resize(frame, (resize_width, new_h), interpolation=cv2.INTER_AREA)

                fname = out_dir / f"frame_{timestamp_ms:010d}.jpg"
                cv2.imwrite(str(fname), frame, encode_params)

                record = {
                    "filename": fname.name,
                    "timestamp_ms": timestamp_ms,
                    "timestamp_sec": round(timestamp_ms / 1000.0, 3),
                    "frame_index": frame_idx,
                }
                index_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                saved += 1

            frame_idx += 1
            pbar.update(1)

    cap.release()
    print(f"[extract_frames] Сохранено {saved} кадров → {out_dir}")
    print(f"[extract_frames] Индекс → {index_path}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
    extract_frames(root / "input" / "video.mp4", cfg, root)
