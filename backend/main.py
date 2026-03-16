# backend/main.py
import asyncio, json, os, shutil, zipfile
from pathlib import Path
import traceback
import multiprocessing
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from session_store import store
from agent import LiveAgent
from csv_parser import profile_csv, load_dataframe
from analysis import analyse
from chart_generator import make_chart
from report_docx import build_docx
from report_pptx import build_pptx
from report_html import build_html
from slide_renderer import render_all_slides, PALETTES
from video_renderer import render_cinematic_video, get_narration_for_slide
from audio_summary import generate_audio_summary, generate_slide_narration

load_dotenv()

multiprocessing.set_start_method('spawn', force=True)
app = FastAPI(title='CaseStudy Forge')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', 'outputs')
UPLOADS_DIR = os.getenv('UPLOADS_DIR', 'uploads')
TEMPLATES_DIR = Path(__file__).parent / 'templates'
FRONTEND_DIR = Path(__file__).parent.parent / 'frontend'

os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


@app.get('/')
async def root():
    index = FRONTEND_DIR / 'index.html'
    return FileResponse(str(index))


@app.get('/audio_processor.js')
async def audio_processor():
    return FileResponse(str(FRONTEND_DIR / 'audio_processor.js'))


@app.post('/session')
async def create_session():
    session = store.create()
    return {'session_id': session.session_id}


@app.post('/upload/{session_id}')
async def upload_csv(session_id: str, file: UploadFile = File(...)):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, 'Session not found')
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, 'Only CSV files accepted')

    dest = os.path.join(UPLOADS_DIR, f'{session_id}_{file.filename}')
    with open(dest, 'wb') as f:
        shutil.copyfileobj(file.file, f)

    session.csv_path = dest
    session.csv_filename = file.filename
    return {'ok': True, 'filename': file.filename}


@app.get('/status/{session_id}')
async def get_status(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, 'Session not found')
    return {
        'status': session.status,
        'transcript': session.transcript,
        'outputs': {k: bool(v) for k, v in session.outputs.items()},
        'error': session.error,
    }


@app.websocket('/ws/voice/{session_id}')
async def voice_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = store.get(session_id)
    if not session:
        await websocket.close(code=4004)
        return

    transcript_chunks = []

    async def on_text(text: str):
        transcript_chunks.append(text)
        session.transcript = ' '.join(transcript_chunks)
        await websocket.send_json({'type': 'transcript', 'text': text})

    agent = LiveAgent(session_id=session_id, on_text=on_text)
    await agent.start()

    receive_task = asyncio.create_task(agent.receive_loop())

    try:
        store.update_status(session_id, 'recording')
        while True:
            data = await websocket.receive_bytes()
            if data == b'__STOP__':
                break
            await agent.send_audio(data)
    except WebSocketDisconnect:
        pass
    finally:
        receive_task.cancel()
        await agent.stop()
        store.update_status(session_id, 'idle')
        await websocket.send_json({'type': 'stopped', 'final_transcript': session.transcript})


@app.post('/generate/{session_id}')
async def generate_report(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, 'Session not found')
    if not session.csv_path:
        raise HTTPException(400, 'No CSV uploaded for this session')

    store.update_status(session_id, 'analysing')
    print("=== GENERATE STARTED ===", flush=True)

    try:
        # ── 1. Profile CSV ───────────────────────────────────────────
        print("=== STEP 1: profiling CSV ===", flush=True)
        csv_profile = profile_csv(session.csv_path)
        df = load_dataframe(session.csv_path)

        # Cap to avoid token overflow
        print("=== STEP 2: trimming profile ===", flush=True)
        csv_profile["sample"] = csv_profile.get("sample", [])[:3]
        if "numeric_stats" in csv_profile:
            cols = list(csv_profile["numeric_stats"].keys())
            csv_profile["numeric_stats"] = {k: csv_profile["numeric_stats"][k] for k in cols[:15]}

        # ── 2. Gemini analysis → SCQA report plan ───────────────────
        print("=== STEP 3: calling Gemini ===", flush=True)
        report_plan = await analyse(csv_profile, session.transcript)
        session.report_plan = report_plan
        print("=== STEP 4: Gemini done ===", flush=True)

        store.update_status(session_id, 'generating')

        # ── 3. Output directories ────────────────────────────────────
        out_dir = os.path.join(OUTPUTS_DIR, session_id)
        charts_dir = os.path.join(out_dir, 'charts')
        slides_dir = os.path.join(out_dir, 'slides')
        audio_dir = os.path.join(out_dir, 'audio')
        os.makedirs(charts_dir, exist_ok=True)
        os.makedirs(slides_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)

        # ── 4. Generate charts (Matplotlib PNG + Plotly JSON) ────────
        print("=== STEP 5: generating charts ===", flush=True)
        charts = []
        for i, section in enumerate(report_plan.get('sections', [])):
            chart_spec = section.get('chart', {})
            chart = make_chart(chart_spec, df, charts_dir, i)
            charts.append(chart)
        session.charts = [c for c in charts if c]

        # ── 5. Generate per-slide narration audio ────────────────────
        print("=== STEP 6: generating audio ===", flush=True)
        sections = report_plan.get('sections', [])
        slide_audio_paths = []

        cover_audio = os.path.join(audio_dir, 'narration_00_cover.mp3')
        generate_audio_summary(report_plan.get('executive_summary', ''), cover_audio)
        slide_audio_paths.append(cover_audio)

        for i, section in enumerate(sections):
            narration_text = get_narration_for_slide(section)
            slide_audio = os.path.join(audio_dir, f'narration_{i+1:02d}.mp3')
            generate_slide_narration(narration_text, slide_audio)
            slide_audio_paths.append(slide_audio)

        conc_audio = os.path.join(audio_dir, 'narration_conclusion.mp3')
        generate_audio_summary(report_plan.get('conclusion', ''), conc_audio)
        slide_audio_paths.append(conc_audio)

        # ── 6. Render cinematic slide PNGs via Playwright ────────────
        print("=== STEP 7: rendering slides ===", flush=True)
        palette_name = report_plan.get('palette', 'midnight')
        slide_png_paths = await render_all_slides(
            report_plan=report_plan,
            charts=session.charts,
            out_dir=slides_dir,
            palette_name=palette_name,
        )

        # ── 7. Compose cinematic MP4 ─────────────────────────────────
        print("=== STEP 8: composing video ===", flush=True)
        video_path = os.path.join(out_dir, 'presentation.mp4')
        await render_cinematic_video(
            report_plan=report_plan,
            charts=session.charts,
            narration_audios=slide_audio_paths,
            output_path=video_path,
        )

        # ── 8. Still generate DOCX, PPTX, HTML for compatibility ─────
        print("=== STEP 9: building docs ===", flush=True)
        docx_path = os.path.join(out_dir, 'report.docx')
        pptx_path = os.path.join(out_dir, 'report.pptx')
        html_path = os.path.join(out_dir, 'report.html')
        mp3_path = os.path.join(out_dir, 'summary.mp3')

        build_docx(report_plan, session.charts, docx_path)
        build_pptx(report_plan, session.charts, pptx_path)
        build_html(report_plan, session.charts, html_path, str(TEMPLATES_DIR))
        generate_audio_summary(report_plan.get('audio_summary_script', ''), mp3_path)

        session.outputs = {
            'mp4': video_path,
            'docx': docx_path,
            'pptx': pptx_path,
            'html': html_path,
            'mp3': mp3_path,
        }

        # ── 9. Bundle ZIP ─────────────────────────────────────────────
        print("=== STEP 10: zipping ===", flush=True)
        zip_path = os.path.join(out_dir, 'report_bundle.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for key, path in session.outputs.items():
                if os.path.exists(path):
                    zf.write(path, os.path.basename(path))
        session.outputs['zip'] = zip_path

        store.update_status(session_id, 'done')
        print("=== GENERATE COMPLETE ===", flush=True)
        return {'ok': True, 'status': 'done'}

    except Exception as e:
        print("=== GENERATE ERROR ===", flush=True)
        print(traceback.format_exc(), flush=True)
        session.status = 'error'
        session.error = str(e)
        raise HTTPException(500, str(e))


class TranscriptIn(BaseModel):
    transcript: str


@app.post('/set-transcript/{session_id}')
async def set_transcript(session_id: str, body: TranscriptIn):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, 'Session not found')
    session.transcript = body.transcript
    return {'ok': True}


@app.get('/download/{session_id}/{filetype}')
async def download(session_id: str, filetype: str):
    session = store.get(session_id)
    if not session or not session.outputs.get(filetype):
        raise HTTPException(404, 'File not found')
    path = session.outputs[filetype]
    media_map = {
        'mp4': 'video/mp4',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'html': 'text/html',
        'mp3': 'audio/mpeg',
        'zip': 'application/zip',
    }
    return FileResponse(
        path,
        media_type=media_map.get(filetype, 'application/octet-stream'),
        filename=os.path.basename(path)
    )