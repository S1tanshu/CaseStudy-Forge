# CaseStudy Forge

> Upload a CSV · Speak your findings · Get a boardroom-ready report

Voice-driven, multimodal business report generation powered by the Gemini Live API. Upload raw data, speak your narrative aloud, and receive five simultaneous outputs: a Word document, PowerPoint, interactive HTML report, MP3 audio summary, and a cinematic narrated MP4 video.

---

## The Problem It Solves

You finish your analysis. You know what the data means. You know the story. But then you spend the next four hours in PowerPoint — manually building charts, formatting slides, writing the same insights in a different window for a different audience. That is not analysis. That is transcription.

CaseStudy Forge eliminates that last mile entirely.

---

## How It Works

1. Upload a raw CSV file (sales data, survey results, financials — any tabular data)
2. Click **Start Recording** and speak your findings naturally
3. Gemini Live API transcribes your voice in real time, streaming text to the screen
4. Click **Stop**, then **Generate Report**
5. The SCQA narrative engine fuses your spoken narrative with auto-generated charts
6. Download five boardroom-ready outputs simultaneously

---

## Output Formats

| File | Description |
|---|---|
| `presentation.mp4` | Cinematic video — Ken Burns slide transitions, ElevenLabs narration, crossfades |
| `report.docx` | Fully formatted Word document with embedded charts and callout boxes |
| `report.pptx` | PowerPoint deck for teams that need editable slides |
| `report.html` | Interactive HTML with live Plotly charts |
| `summary.mp3` | Standalone audio summary for listening on the go |
| `report_bundle.zip` | All five files in one download |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Voice AI | Gemini Live API (`gemini-2.5-flash-live-001`) — bidirectional audio streaming |
| Analysis | Gemini Flash (`gemini-2.5-flash`) — SCQA narrative engine |
| Backend | FastAPI + Python 3.12, uvicorn |
| TTS | ElevenLabs Turbo v2.5 (gTTS fallback when key is absent) |
| Slide rendering | Playwright (headless Chromium) → 1920×1080 PNG |
| Video | moviepy 1.0.3 + ffmpeg — Ken Burns zoom + crossfade transitions |
| Charts | Matplotlib (static PNG) + Plotly (interactive JSON) |
| Frontend | Vanilla JS, single HTML file, Web Audio API, AudioWorklet PCM resampler |

### Google Cloud APIs Used
- **Gemini Live API** (`generativelanguage.googleapis.com`) — real-time voice transcription via `google-genai` SDK → [`backend/agent.py`](backend/agent.py)
- **Gemini Flash API** — SCQA narrative analysis and structured JSON report planning → [`backend/analysis.py`](backend/analysis.py)

---

## Local Setup — Step by Step

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.12+ | 3.11 also works |
| ffmpeg | Required by moviepy for video encoding |
| Google AI Studio key | Free at [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| ElevenLabs key (optional) | Free tier at [elevenlabs.io](https://elevenlabs.io) — gTTS used as fallback |

**Install ffmpeg:**
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html and add to PATH
```

### Step 1 — Clone the repository

```bash
git clone https://github.com/S1tanshu/casestudy-forge.git
cd casestudy-forge
```

### Step 2 — Create a Python virtual environment

```bash
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — Mac / Linux
source venv/bin/activate
```

### Step 3 — Install Python dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 4 — Install Playwright browser

```bash
playwright install chromium
```

### Step 5 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```bash
GEMINI_API_KEY=your_google_ai_studio_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here      # optional, gTTS used if absent
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL        # Sarah voice (warm, professional)
APP_HOST=127.0.0.1
APP_PORT=8080
OUTPUTS_DIR=outputs
UPLOADS_DIR=uploads
```

### Step 6 — Run the server

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

### Step 7 — Open the app

```
http://127.0.0.1:8080
```

---

## Test With Sample Data

Run this once to generate a demo CSV (96 rows, 4 regions, 12 months):

```python
import pandas as pd
import numpy as np

months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
regions = ['APAC','EMEA','AMER','LATAM']
rows = []
for month in months:
    for region in regions:
        rows.append({
            'Month': month,
            'Region': region,
            'Revenue': int(np.random.randint(50000, 500000)),
            'Units_Sold': int(np.random.randint(100, 2000)),
            'Gross_Margin_Pct': round(np.random.uniform(0.25, 0.65), 2),
            'Customer_Count': int(np.random.randint(20, 300)),
        })
pd.DataFrame(rows).to_csv('sample_sales.csv', index=False)
print('Created sample_sales.csv')
```

**Demo speaking prompt:**
> "APAC revenue grew 40% in Q3 driven by new enterprise accounts. EMEA had a slow H1 but recovered well in October. Gross margins are healthy across all regions. The big opportunity is LATAM — it is severely underpenetrated."

---

## Project Structure

```
casestudy-forge/
├── backend/
│   ├── main.py               # FastAPI app — all HTTP + WebSocket endpoints
│   ├── agent.py              # Gemini Live API session manager (Google Cloud)
│   ├── analysis.py           # Gemini Flash SCQA narrative engine (Google Cloud)
│   ├── csv_parser.py         # CSV ingestion + statistical profiling
│   ├── chart_generator.py    # Matplotlib PNG + Plotly interactive charts
│   ├── slide_renderer.py     # HTML design system → Playwright → 1920×1080 PNG
│   ├── render_slide_worker.py# Subprocess worker (Windows ProactorEventLoop fix)
│   ├── video_renderer.py     # moviepy Ken Burns video composer
│   ├── audio_summary.py      # ElevenLabs TTS with gTTS fallback
│   ├── report_docx.py        # python-docx builder
│   ├── report_pptx.py        # python-pptx builder
│   ├── report_html.py        # Jinja2 HTML report builder
│   ├── session_store.py      # In-memory session state
│   └── templates/
│       └── report.html.j2    # Jinja2 HTML report template
├── frontend/
│   ├── index.html            # Single-file UI — HTML + CSS + JS
│   └── audio_processor.js   # AudioWorklet PCM resampler (48kHz → 16kHz)
├── .env.example
├── Dockerfile
├── cloudbuild.yaml
└── README.md
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/session` | Create session → returns `session_id` |
| `POST` | `/upload/{session_id}` | Upload CSV |
| `WS` | `/ws/voice/{session_id}` | Stream PCM audio → receive live transcript |
| `POST` | `/generate/{session_id}` | Trigger full report generation pipeline |
| `GET` | `/status/{session_id}` | Poll pipeline status + progress |
| `GET` | `/download/{session_id}/{type}` | Download `mp4/docx/pptx/html/mp3/zip` |

---

## Known Platform Notes

- **Windows:** Playwright runs via `subprocess.run` to a separate `render_slide_worker.py` to bypass the `ProactorEventLoop` incompatibility with uvicorn.
- **Pillow:** Must be pinned to `9.5.0`. Newer versions removed `PIL.Image.ANTIALIAS` which moviepy 1.0.3 depends on. A one-line monkey patch at the top of `main.py` handles this.
- **moviepy:** Must be `1.0.3`. Version 2 introduced breaking API changes.
- **Video generation** (Step 8) is CPU-intensive. On slow hardware, expect 3–5 minutes for a 6-slide video.

---

## Proof of Google Cloud Usage

This project calls two Google Cloud APIs:

- **Gemini Live API** (`gemini-2.5-flash-live-001`) — bidirectional audio streaming for real-time voice transcription: [`backend/agent.py`](backend/agent.py)
- **Gemini Flash API** (`gemini-2.5-flash`) — SCQA narrative analysis, structured JSON report planning: [`backend/analysis.py`](backend/analysis.py)

Both are called via the official `google-genai` Python SDK, connecting to `generativelanguage.googleapis.com`.

---

## Built For

**Gemini Live Agent Challenge** — Google DeepMind
