# CaseStudy Forge

> Upload a CSV · Speak your findings · Get a boardroom-ready report

Voice-driven, multimodal business report generation. Upload raw data, speak your narrative aloud via the Gemini Live API, and receive boardroom-ready outputs: DOCX, PPTX, Interactive HTML, MP3 audio summary, and a cinematic MP4 video.

---

## What It Does

1. Upload a CSV file (sales data, survey results, financials — anything tabular)
2. Click **Start Recording** and speak your findings naturally
3. Gemini Live transcribes in real-time
4. Click **Generate** — the agent fuses your voice narrative with auto-generated charts
5. Download: Word doc, PowerPoint, Interactive HTML, Audio summary, and Cinematic video

## Why This Gap Exists

Tools like Gamma and Beautiful.ai generate slides from prompts. None of them:
- Accept raw CSV as primary input
- Use voice as the main interface
- Weave spoken narration with auto-generated charts
- Produce five output formats simultaneously from one session

---

## Tech Stack

| Layer | Technology |
|---|---|
| Voice AI | Gemini Live API (`gemini-2.0-flash-live`) |
| Analysis | Gemini Flash (`gemini-2.0-flash`) — SCQA narrative engine |
| Backend | FastAPI + Python 3.12 |
| TTS | ElevenLabs Turbo v2.5 (gTTS fallback) |
| Slide rendering | Playwright (headless Chromium) → 1920×1080 PNG |
| Video | moviepy 1.0.3 + ffmpeg — Ken Burns effect + crossfade transitions |
| Charts | Matplotlib (static) + Plotly (interactive) |
| Outputs | DOCX · PPTX · HTML · MP3 · MP4 |

---

## Local Setup

### Prerequisites
- Python 3.12+
- ffmpeg installed (`brew install ffmpeg` / `apt install ffmpeg` / Windows: download from ffmpeg.org)
- A [Google AI Studio](https://aistudio.google.com/app/apikey) API key
- An [ElevenLabs](https://elevenlabs.io) API key (free tier works; gTTS fallback if absent)

### Install
```bash
git clone https://github.com/YOUR_USERNAME/casestudy-forge
cd casestudy-forge

python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r backend/requirements.txt
playwright install chromium
```

### Configure
```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### Run
```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

Open `http://127.0.0.1:8080`

---

## Deployment (Google Cloud Run)

See [Cloud Run Deployment](#) section below or use the included `Dockerfile` and `cloudbuild.yaml`.

---

## Project Structure
```
casestudy-forge/
├── backend/
│   ├── main.py               # FastAPI app — all endpoints
│   ├── agent.py              # Gemini Live session manager
│   ├── analysis.py           # SCQA narrative engine (Gemini Flash)
│   ├── csv_parser.py         # CSV ingestion + profiling
│   ├── chart_generator.py    # Matplotlib + Plotly charts
│   ├── slide_renderer.py     # HTML design system → Playwright PNG
│   ├── video_renderer.py     # moviepy Ken Burns video composer
│   ├── audio_summary.py      # ElevenLabs TTS (gTTS fallback)
│   ├── report_docx.py        # python-docx builder
│   ├── report_pptx.py        # python-pptx builder
│   ├── report_html.py        # Jinja2 HTML builder
│   ├── session_store.py      # In-memory session state
│   └── templates/
│       └── report.html.j2
├── frontend/
│   ├── index.html
│   └── audio_processor.js
├── .env.example
├── Dockerfile
├── cloudbuild.yaml
└── README.md
```

---

## Known Constraints

- Video composition (Step 8) is CPU-intensive. On Cloud Run, set `--memory=4Gi --cpu=2`.
- Playwright requires Chromium — already included in the Dockerfile.
- Windows local dev: Playwright runs via subprocess worker to avoid `ProactorEventLoop` issues.

---

## Built For

Gemini Live Agent Challenge — Google DeepMind
