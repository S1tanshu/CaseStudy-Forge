# CaseStudy Forge 🎙️→📊

> Upload a CSV. Speak your findings. Get a boardroom-ready report in minutes.

CaseStudy Forge is a voice-driven, multimodal business report generator built for the **Gemini Live Agent Challenge**. It combines real-time voice input via the Gemini Live API, structured data analysis, animated Chart.js visualisations, ElevenLabs narration, and Playwright-recorded cinematic video — all in one pipeline.

**Outputs per session:** MP4 video · DOCX · PPTX · Interactive HTML · MP3 summary · ZIP bundle

---

## Architecture

```
User speaks findings
        │
        ▼
Gemini Live API  ──────────────────────────────────────────┐
(gemini-2.5-flash)                                         │
  Voice → Transcript → SCQA Report Plan (JSON)             │
        │                                                   │
        ▼                                                   │
  CSV Profile (pandas)                                      │
        │                                                   │
        ▼                                                   │
  Chart Generator  ──── Plotly JSON + Matplotlib PNG        │
        │                                                   │
        ▼                                                   │
  ElevenLabs TTS  ──── Per-slide narration MP3s             │
        │                                                   │
        ▼                                                   │
  Playwright Slide Renderer ──── Static slide PNGs          │
        │                                                   │
        ▼                                                   │
  Video Renderer (Playwright screen recording)              │
    • Animated HTML (Chart.js: bars grow, pies draw)        │
    • CSS transitions (slide-up, fade, wipe, scale)         │
    • ffmpeg adelay audio sync + H.264 mux                  │
        │                                                   │
        ▼                                                   │
  Document Builder ──── DOCX + PPTX + HTML + MP3           │
        │                                                   │
        ▼                                                   │
       ZIP  ←──────────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12 |
| ffmpeg + ffprobe | Any recent build |
| Node.js | Not required |
| OS | Windows 10/11, macOS, Ubuntu |

---

## Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/casestudy-forge.git
cd casestudy-forge
```

---

## Step 2 — Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

---

## Step 3 — Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Key packages:**
```
fastapi==0.111.0
uvicorn==0.29.0
google-genai>=0.5.0
playwright==1.44.0
python-docx==1.1.2
python-pptx==0.6.23
pandas==2.2.2
matplotlib==3.9.0
plotly==5.22.0
kaleido==0.2.1
elevenlabs==1.2.0
gTTS==2.5.1
python-dotenv==1.0.1
Jinja2==3.1.4
Pillow==10.3.0
ffmpeg-python==0.2.0
```

---

## Step 4 — Install Playwright's Chromium browser

```bash
playwright install chromium
```

---

## Step 5 — Install ffmpeg

**Windows (via winget):**
```bash
winget install ffmpeg
```
Then restart your terminal and verify:
```bash
ffmpeg -version
ffprobe -version
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu:**
```bash
sudo apt update && sudo apt install ffmpeg
```

---

## Step 6 — Configure environment variables

Create a `.env` file inside the `backend/` directory:

```bash
# backend/.env

GEMINI_API_KEY=your_google_ai_studio_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here   # optional — gTTS runs without it
OUTPUTS_DIR=outputs
UPLOADS_DIR=uploads
```

Get your Gemini API key free at: https://aistudio.google.com/app/apikey

---

## Step 7 — Enable long paths (Windows only)

Run PowerShell as Administrator:
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

## Step 8 — Run the app

```bash
# Make sure you are inside the backend/ directory
cd backend
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

Open your browser at: **http://127.0.0.1:8080**

---

## How to use

1. Click **Upload CSV** and select your data file
2. Click **Start Recording** and speak your findings naturally (20–60 seconds)
3. Click **Stop** then **Generate Report**
4. Wait ~5–10 minutes for the full pipeline to complete
5. Download your ZIP bundle containing all outputs

---

## Sample data for testing

A pre-built sample dataset and transcript are included:

```
sample_data/
├── sample_data.csv        # 96-row SaaS revenue dataset (4 regions, 4 products, 6 quarters)
└── sample_findings.txt      # Pre-written transcript — paste into the voice box
```

This dataset is designed to produce bars, pies, and line charts in the video.

---

## Project structure

```
casestudy-forge/
├── backend/
│   ├── main.py                  # FastAPI app — full generation pipeline
│   ├── agent.py                 # Gemini Live voice session handler
│   ├── analysis.py              # Gemini SCQA report plan generator
│   ├── chart_generator.py       # Matplotlib + Plotly chart renderer
│   ├── audio_summary.py         # ElevenLabs / gTTS narration generator
│   ├── slide_renderer.py        # Playwright static slide PNG renderer
│   ├── video_renderer.py        # Playwright screen recording + Chart.js video
│   ├── report_docx.py           # python-docx DOCX builder
│   ├── report_pptx.py           # python-pptx PPTX builder
│   ├── report_html.py           # Jinja2 HTML report builder
│   ├── csv_parser.py            # pandas CSV profiler
│   ├── session_store.py         # In-memory session state
│   ├── google_cloud_services.py # GCP / Gemini API integration proof
│   ├── templates/               # Jinja2 HTML templates
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Single-page UI
│   └── audio_processor.js       # Web Audio worklet for PCM streaming
├── sample_data/
│   ├── sample_techco.csv
│   └── sample_findings.txt
├── .env.example
└── README.md
```

---

## Google Cloud services used

| Service | Purpose |
|---|---|
| **Gemini Live API** (`gemini-2.5-flash`) | Real-time voice transcription + SCQA narrative generation |
| **Google AI Studio** | API key management |

See `backend/google_cloud_services.py` for explicit API integration code.

---

## Generation pipeline steps

| Step | What happens |
|---|---|
| 1 | Profile CSV with pandas |
| 2 | Trim profile to fit token budget |
| 3 | Call Gemini Live API → SCQA report plan |
| 4 | Gemini response received |
| 5 | Generate charts (Matplotlib PNG + Plotly JSON) |
| 6 | Generate per-slide narration audio (ElevenLabs / gTTS) |
| 7 | Render static slide PNGs via Playwright |
| 8 | Record animated video via Playwright screen recording |
| 9 | Build DOCX + PPTX + HTML + MP3 |
| 10 | Bundle ZIP |

---

## Troubleshooting

**`Could not import module "main"`**
Make sure you are running uvicorn from *inside* the `backend/` directory, not from the project root.

**`NotImplementedError` from Playwright**
This is a Windows event loop issue. The fix is already applied in `video_renderer.py` — Playwright runs in a `ProactorEventLoop` thread.

**`ffmpeg returned non-zero exit status`**
Run `ffmpeg -version` in your terminal. If it's not found, ffmpeg is not on your PATH — reinstall and restart your terminal.

**Video renders but no animations visible**
Make sure `--disable-gpu` is NOT in the Playwright launch args in `video_renderer.py`. GPU compositing is required for CSS animations.

**ElevenLabs not working**
The pipeline falls back to gTTS automatically if `ELEVENLABS_API_KEY` is missing or the request fails. The video will still generate with gTTS narration.
