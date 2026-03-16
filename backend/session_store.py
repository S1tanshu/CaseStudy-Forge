# backend/session_store.py
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional
 
 
@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    csv_path: Optional[str] = None
    csv_filename: Optional[str] = None
    transcript: str = ''
    report_plan: Optional[dict] = None
    charts: list = field(default_factory=list)  # [{title, png_path, plotly_json}]
    outputs: dict = field(default_factory=dict)  # {docx, html, pptx, mp3}
    status: str = 'idle'  # idle | recording | analysing | generating | done | error
    error: Optional[str] = None
 
 
class SessionStore:
    def __init__(self):
        self._store: dict[str, Session] = {}
 
    def create(self) -> Session:
        s = Session()
        self._store[s.session_id] = s
        return s
 
    def get(self, session_id: str) -> Optional[Session]:
        return self._store.get(session_id)
 
    def update_status(self, session_id: str, status: str):
        if s := self._store.get(session_id):
            s.status = status
 
    def cleanup_old(self, max_age_seconds: int = 3600):
        """Remove sessions older than max_age_seconds."""
        now = time.time()
        self._store = {
            k: v for k, v in self._store.items()
            if now - v.created_at < max_age_seconds
        }
 
 
# Global singleton
store = SessionStore()
