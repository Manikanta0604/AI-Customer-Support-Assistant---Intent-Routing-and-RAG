from functools import lru_cache
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import Database
from .knowledge import KnowledgeStore, extract_text
from .schemas import ChatRequest, ChatResponse, Escalation, EscalationUpdate, Message
from .service import SupportService

settings = get_settings()
app = FastAPI(title="AI Customer Support Assistant", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=["*"], allow_headers=["*"])


@lru_cache
def database() -> Database:
    return Database(settings.database_path)


@lru_cache
def knowledge() -> KnowledgeStore:
    store = KnowledgeStore(settings)
    starter = Path(settings.starter_knowledge_path)
    if store.is_empty() and starter.exists():
        store.index(starter.name, starter.read_text())
    return store


def service(db: Database = Depends(database), store: KnowledgeStore = Depends(knowledge)) -> SupportService:
    return SupportService(settings, db, store)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": settings.llm_provider}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, support: SupportService = Depends(service)):
    return await support.chat(request)


@app.get("/api/sessions/{session_id}", response_model=list[Message])
def history(session_id: str, db: Database = Depends(database)):
    return db.history(session_id, limit=100)


@app.post("/api/knowledge", status_code=201)
async def upload_knowledge(file: UploadFile = File(...), store: KnowledgeStore = Depends(knowledge)):
    content = await file.read()
    try:
        text = extract_text(file.filename or "knowledge.txt", content)
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    if not text.strip():
        raise HTTPException(422, "No readable content found")
    return {"source": file.filename, "chunks": store.index(file.filename or "knowledge.txt", text)}


@app.get("/api/escalations", response_model=list[Escalation])
def list_escalations(db: Database = Depends(database)):
    return db.escalations()


@app.patch("/api/escalations/{case_id}", status_code=204)
def update_escalation(case_id: int, update: EscalationUpdate, db: Database = Depends(database)):
    if not db.update_escalation(case_id, update.status):
        raise HTTPException(404, "Escalation not found")
