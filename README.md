# UX Rule Video Agent

Локальный Python-инструмент для анализа UX-видео, где бухгалтер создает правила на операции клиента.

## Вход

Положить файлы:

```text
input/video.mp4
input/transcript.txt
```

---

## Установка

```bash
# Создать и активировать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows

# Установить зависимости
pip install -r requirements.txt

# Заполнить .env
cp .env.example .env
# Откройте .env и вставьте реальный OPENROUTER_API_KEY
```

---

## Запуск

### Полный пайплайн

```bash
python src/run_pipeline.py \
    --video input/video.mp4 \
    --transcript input/transcript.txt \
    --config config.json
```

### По одному шагу

```bash
# Шаг 1: нарезать кадры из видео
python src/run_pipeline.py --step extract --video input/video.mp4

# Шаг 2: отфильтровать кадры и собрать сцены
python src/run_pipeline.py --step scenes

# Шаг 3: проанализировать каждую сцену через ИИ
python src/run_pipeline.py --step analyze --transcript input/transcript.txt

# Шаг 4: собрать итоговый отчёт
python src/run_pipeline.py --step report
```

---

## Входные файлы

| Файл | Описание |
|---|---|
| `input/video.mp4` | Запись экрана |
| `input/transcript.txt` | Расшифровка разговора |

### Форматы транскрипта

```
[00:01:23] Бухгалтер открыл ленту операций...
[01:45] Выбирает операцию по контрагенту...
```

Или простой текст без таймкодов — будет принят как единый блок.

---

## Структура проекта

```
ux-rule-video-agent/
  input/
    video.mp4                       ← входное видео
    transcript.txt                  ← расшифровка разговора

  output/
    frames_raw/                     ← все нарезанные кадры (JPEG)
    frames_kept/                    ← отфильтрованные уникальные кадры
    frames_index.jsonl              ← индекс всех нарезанных кадров
    scenes.jsonl                    ← список сцен
    scene_manifest.json             ← сводный манифест сцен
    scene_packets/
      scene_0001/
        frame_XXXXXXXXXX.jpg        ← кадры сцены
        scene.json                  ← метаданные сцены
      scene_0002/ ...
    chunks/
      scene_analyses.jsonl          ← JSON-анализ каждой сцены от модели
    reports/
      final_report.md               ← итоговый Markdown-отчёт
      ux_rule_creation_analysis.xlsx ← Excel-отчёт (4 листа)

  prompts/
    scene_analysis_prompt.md        ← промпт анализа одной сцены
    final_report_prompt.md          ← промпт итогового отчёта

  src/
    extract_frames.py               ← шаг 1: нарезка видео
    build_scenes.py                 ← шаг 2: фильтрация и группировка в сцены
    analyze_scenes.py               ← шаг 3: анализ через OpenRouter
    build_report.py                 ← шаг 4: сборка отчётов
    run_pipeline.py                 ← точка входа

  .cursor/
    rules/
      ux-rule-video-agent.mdc

  .env.example
  .env                              ← не коммитить
  config.json
  requirements.txt
  README.md
```

---

## Параметры config.json

| Параметр | По умолчанию | Описание |
|---|---|---|
| `sample_fps` | 2.0 | Частота нарезки кадров (кадров/сек) |
| `jpeg_quality` | 85 | Качество JPEG |
| `resize_width` | 1600 | Максимальная ширина кадра (px) |
| `min_keep_gap_sec` | 2.0 | Минимальный интервал между сохранёнными кадрами |
| `force_keep_every_sec` | 15.0 | Принудительное сохранение кадра раз в N сек |
| `pixel_diff_threshold` | 3.0 | Порог попиксельной разницы |
| `phash_distance_threshold` | 8 | Порог расстояния pHash |
| `scene_break_gap_sec` | 20.0 | Пауза для разделения сцен |
| `max_frames_per_scene` | 4 | Максимум кадров на сцену в промпте |
| `max_previous_summary_chars` | 300 | Длина контекста предыдущей сцены |
| `request_timeout_sec` | 180 | Таймаут запроса к API |
| `max_retries` | 4 | Повторные попытки при ошибке |
| `retry_backoff_sec` | 2.5 | Базовая задержка перед повтором |
| `openrouter_temperature` | 0.1 | Температура модели |
| `openrouter_max_tokens` | 2200 | Максимум токенов в ответе |

---

## Переменные .env

```env
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemini-2.5-pro
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_HTTP_REFERER=https://your-company.example
OPENROUTER_X_TITLE=UX Rule Video Agent
```

---

## Требования

- Python 3.12+
- ffmpeg не нужен — видео читается через `opencv-python` напрямую
