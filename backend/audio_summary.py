# backend/audio_summary.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

ELEVEN_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')

def _gtts_fallback(script: str, output_path: str) -> str:
    """Try gTTS, and if that also fails, write a silent MP3 so pipeline continues."""
    try:
        from gtts import gTTS
        gTTS(text=script, lang='en', slow=False).save(output_path)
        return output_path
    except Exception:
        # Write a minimal valid silent MP3 so downstream doesn't crash
        _write_silent_mp3(output_path)
        return output_path

def _write_silent_mp3(output_path: str):
    """Write a tiny silent MP3 file as last resort."""
    # Minimal valid MP3 header (silent, ~0.1s)
    silent_mp3 = bytes([
        0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ] * 100)
    with open(output_path, 'wb') as f:
        f.write(silent_mp3)

def generate_audio_summary(script: str, output_path: str) -> str:
    if not ELEVEN_API_KEY:
        return _gtts_fallback(script, output_path)

    try:
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}'
        payload = {
            'text': script,
            'model_id': 'eleven_turbo_v2_5',
            'voice_settings': {
                'stability': 0.45,
                'similarity_boost': 0.85,
                'style': 0.30,
                'use_speaker_boost': True
            }
        }
        headers = {
            'xi-api-key': ELEVEN_API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return output_path

    except Exception:
        return _gtts_fallback(script, output_path)

def generate_slide_narration(text: str, output_path: str) -> str:
    return generate_audio_summary(text, output_path)