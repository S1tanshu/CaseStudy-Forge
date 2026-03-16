# backend/agent.py
import asyncio
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
 
load_dotenv()
 
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
 
TRANSCRIPTION_PROMPT = '''
You are a voice transcription agent for CaseStudy Forge.
Your ONLY job is to transcribe the user's spoken words accurately.
Output ONLY the transcription — no commentary, no punctuation added beyond natural sentence boundaries.
Do not summarise. Do not interpret. Transcribe verbatim.
'''
 
 
class LiveAgent:
    def __init__(self, session_id: str, on_text: callable):
        self.session_id = session_id
        self.on_text = on_text  # async callback: on_text(text_chunk: str)
        self._live_session = None
        self._running = False
 
    async def start(self):
        """Connect to Gemini Live API."""
        config = types.LiveConnectConfig(
            response_modalities=['TEXT'],  # We want text transcription, not audio
            system_instruction=TRANSCRIPTION_PROMPT,
        )
        self._ctx = client.aio.live.connect(
            model='models/gemini-2.0-flash-live-001',
            config=config
        )
        self._live_session = await self._ctx.__aenter__()
        self._running = True
 
    async def send_audio(self, pcm_bytes: bytes):
        """Send a chunk of PCM16 16kHz mono audio."""
        if self._live_session and self._running:
            await self._live_session.send(
                input=types.LiveClientRealtimeInput(
                    media_chunks=[types.Blob(data=pcm_bytes, mime_type='audio/pcm;rate=16000')]
                )
            )
 
    async def receive_loop(self):
        """Continuously receive transcription chunks and call on_text."""
        async for response in self._live_session.receive():
            if not self._running:
                break
            if response.text:
                await self.on_text(response.text)
 
    async def stop(self):
        """Gracefully close the Gemini Live session."""
        self._running = False
        if self._live_session:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception:
                pass
        self._live_session = None
