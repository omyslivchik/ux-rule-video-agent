"""
Шаг 2. Фильтрует похожие кадры и группирует их в сцены.

Алгоритм фильтрации:
- Считает pHash каждого кадра.
- Отбрасывает кадры слишком похожие на предыдущий сохранённый
  (расстояние Хэмминга < phash_distance_threshold И pixel_diff < порога),
  если прошло меньше min_keep_gap_sec.
- Каждые force_keep_every_sec секунд принудительно сохраняет кадр.

Группировка в сцены:
- Если разрыв между соседними kept-кадрами > scene_break_gap_sec — новая сцена.
- Из каждой сцены выбирает до max_frames_per_scene кадров (равномерная выборка).

Сохраняет:
- output/frames_kept/frame_XXXXXXXXXX.jpg
- output/scenes.jsonl                          — одна запись на сцену
- output/scene_manifest.json                   — сводный манифест
- output/scene_packets/scene_0001/             — папка на каждую сцену
    frame_XXXXXXXXXX.jpg                       — симлинки / копии кадров сцены
    scene.json                                 — метаданные сцены
"""

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

import imagehash
import numpy as np
from PIL import Image
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _ms_from_name(stem: str) -> Optional[int]:
    m = re.search(r"frame_(\d+)", stem)
    return int(m.group(1)) if m else None


def _pixel_diff(img_a: Image.Image, img_b: Image.Image) -> float:
    a = np.array(img_a.convert("L"), dtype=np.float32)
    b = np.array(img_b.convert("L"), dtype=np.float32)
    if a.shape != b.shape:
        b = np.array(
            img_b.convert("L").resize((a.shape[1], a.shape[0]), Image.LANCZOS),
            dtype=np.float32,
        )
    return float(np.mean(np.abs(a - b)))


def _evenly_sample(items: list, n: int) -> list:
    if len(items) <= n:
        return items
    indices = [round(i * (len(items) - 1) / (n - 1)) for i in range(n)]
    return [items[i] for i in sorted(set(indices))]


# ---------------------------------------------------------------------------
# Фильтрация кадров
# ---------------------------------------------------------------------------

def filter_frames(
    frames_raw_dir: Path,
    frames_kept_dir: Path,
    config: dict,
) -> list[dict]:
    """Возвращает список {"path": Path, "timestamp_ms": int, "timestamp_sec": float}."""
    frames_kept_dir.mkdir(parents=True, exist_ok=True)

    min_gap_ms = int(config["min_keep_gap_sec"] * 1000)
    force_every_ms = int(config["force_keep_every_sec"] * 1000)
    pixel_threshold: float = config["pixel_diff_threshold"]
    phash_threshold: int = config["phash_distance_threshold"]

    all_frames = sorted(frames_raw_dir.glob("frame_*.jpg"))
    if not all_frames:
        print("[build_scenes] Нет кадров в frames_raw/", file=sys.stderr)
        return []

    kept: list[dict] = []
    last_kept_ms: int = -999_999
    last_forced_ms: int = -999_999
    last_hash: Optional[imagehash.ImageHash] = None
    last_img: Optional[Image.Image] = None

    for fpath in tqdm(all_frames, desc="filter_frames", unit="frame"):
        ts_ms = _ms_from_name(fpath.stem)
        if ts_ms is None:
            continue

        img = Image.open(fpath)
        h = imagehash.phash(img)

        gap_ms = ts_ms - last_kept_ms
        force = (ts_ms - last_forced_ms) >= force_every_ms

        if force:
            accept = True
        elif gap_ms < min_gap_ms:
            accept = False
        else:
            pdiff = _pixel_diff(img, last_img) if last_img is not None else 999.0
            hdiff = int(h - last_hash) if last_hash is not None else 99
            accept = pdiff >= pixel_threshold or hdiff >= phash_threshold

        if accept:
            dest = frames_kept_dir / fpath.name
            shutil.copy2(fpath, dest)
            kept.append({
                "path": dest,
                "timestamp_ms": ts_ms,
                "timestamp_sec": round(ts_ms / 1000.0, 3),
            })
            last_kept_ms = ts_ms
            last_hash = h
            last_img = img
            if force:
                last_forced_ms = ts_ms

    print(f"[build_scenes] Отфильтровано: оставлено {len(kept)} из {len(all_frames)} кадров")
    return kept


# ---------------------------------------------------------------------------
# Группировка в сцены
# ---------------------------------------------------------------------------

def build_scenes(
    kept_frames: list[dict],
    session_dir: Path,
    config: dict,
) -> list[dict]:
    scene_break_ms = int(config["scene_break_gap_sec"] * 1000)
    max_frames: int = config["max_frames_per_scene"]

    # Разбить на группы по паузам
    raw_groups: list[list[dict]] = []
    current: list[dict] = []
    for frame in kept_frames:
        if not current:
            current.append(frame)
        elif frame["timestamp_ms"] - current[-1]["timestamp_ms"] > scene_break_ms:
            raw_groups.append(current)
            current = [frame]
        else:
            current.append(frame)
    if current:
        raw_groups.append(current)

    scenes_jsonl_path = session_dir / "scenes.jsonl"
    packets_dir = session_dir / "scene_packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    scene_list: list[dict] = []

    with open(scenes_jsonl_path, "w", encoding="utf-8") as jsonl_file:
        for idx, frames in enumerate(tqdm(raw_groups, desc="build_scenes", unit="scene")):
            scene_num = idx + 1
            scene_id = f"scene_{scene_num:04d}"

            start_ms = frames[0]["timestamp_ms"]
            end_ms = frames[-1]["timestamp_ms"]
            start_sec = round(start_ms / 1000.0, 2)
            end_sec = round(end_ms / 1000.0, 2)

            sampled = _evenly_sample(frames, max_frames)

            # Папка сцены
            scene_dir = packets_dir / scene_id
            scene_dir.mkdir(exist_ok=True)

            frame_paths_in_packet: list[str] = []
            for f in sampled:
                dest = scene_dir / f["path"].name
                shutil.copy2(f["path"], dest)
                frame_paths_in_packet.append(str(dest))

            scene = {
                "scene_id": scene_id,
                "scene_num": scene_num,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 2),
                "total_kept_frames": len(frames),
                "sampled_frame_count": len(sampled),
                "frame_paths": frame_paths_in_packet,
            }

            # scene.json внутри папки сцены
            (scene_dir / "scene.json").write_text(
                json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            jsonl_file.write(json.dumps(scene, ensure_ascii=False) + "\n")
            scene_list.append(scene)

    # Сводный манифест
    manifest = {
        "total_scenes": len(scene_list),
        "total_kept_frames": len(kept_frames),
        "scenes": scene_list,
    }
    manifest_path = session_dir / "scene_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[build_scenes] Сформировано {len(scene_list)} сцен")
    print(f"[build_scenes] scenes.jsonl → {scenes_jsonl_path}")
    print(f"[build_scenes] scene_manifest.json → {manifest_path}")
    print(f"[build_scenes] scene_packets/ → {packets_dir}")
    return scene_list


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def run(config: dict, project_root: Path, session_dir: Path = None) -> list[dict]:
    if session_dir is None:
        session_dir = project_root / "output"
    frames_raw_dir = session_dir / "frames_raw"
    frames_kept_dir = session_dir / "frames_kept"

    kept_frames = filter_frames(frames_raw_dir, frames_kept_dir, config)
    if not kept_frames:
        print("[build_scenes] Нет кадров для группировки.", file=sys.stderr)
        return []

    return build_scenes(kept_frames, session_dir, config)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
    run(cfg, root)
