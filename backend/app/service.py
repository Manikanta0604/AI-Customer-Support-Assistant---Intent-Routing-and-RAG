import httpx
from .config import Settings
from .database import Database
from .intent import route_intent
from .knowledge import KnowledgeStore
from .schemas import ChatRequest, ChatResponse, Citation


class SupportService:
    def __init__(self, settings: Settings, database: Database, knowledge: KnowledgeStore):
        self.settings, self.database, self.knowledge = settings, database, knowledge

    async def chat(self, request: ChatRequest) -> ChatResponse:
        session_id = self.database.ensure_session(request.session_id)
        self.database.add_message(session_id, "user", request.message)
        route = route_intent(request.message)
        citations = self.knowledge.search(request.message)
        low_confidence = not citations or citations[0].score < self.settings.escalation_threshold
        repeated_failure = self.database.unresolved_count(session_id) >= 2
        reason = route.urgent_reason or ("Low knowledge-base confidence" if low_confidence else None) or ("Repeated unresolved responses" if repeated_failure else None)
        if reason:
            answer = "I’m escalating this conversation to a human support specialist. They will have the conversation context and your latest message."
            escalation_id = self.database.escalate(session_id, reason, request.message)
            message_id = self.database.add_message(session_id, "assistant", answer, route.intent)
            return ChatResponse(session_id=session_id, message_id=message_id, answer=answer, intent=route.intent, confidence=route.confidence, citations=citations, escalated=True, escalation_id=escalation_id)

        history = self.database.history(session_id)
        answer, resolved = await generate_answer(request.message, history, citations, self.settings)
        self.database.mark_unresolved(session_id, not resolved)
        message_id = self.database.add_message(session_id, "assistant", answer, route.intent)
        return ChatResponse(session_id=session_id, message_id=message_id, answer=answer, intent=route.intent, confidence=route.confidence, citations=citations, escalated=False)


async def generate_answer(question, history, citations: list[Citation], settings: Settings) -> tuple[str, bool]:
    context = "\n\n".join(f"[{i}] {item.source} / {item.section or 'General'}: {item.passage}" for i, item in enumerate(citations, 1))
    transcript = "\n".join(f"{item.role}: {item.content}" for item in history[-6:])
    prompt = f"You are a concise customer-support assistant. Answer only from context, preserve conversation continuity, and cite claims with [1]. If context is insufficient, say you cannot resolve it.\nConversation:\n{transcript}\nQuestion: {question}\nContext:\n{context}"
    provider = settings.llm_provider.lower()
    if provider == "groq" and settings.groq_api_key:
        return await _openai("https://api.groq.com/openai/v1/chat/completions", settings.groq_api_key, "llama-3.3-70b-versatile", prompt), True
    if provider == "mistral" and settings.mistral_api_key:
        return await _openai("https://api.mistral.ai/v1/chat/completions", settings.mistral_api_key, "mistral-large-latest", prompt), True
    if provider == "gemini" and settings.google_api_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.google_api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"], True
    return f"Here’s what I found: {citations[0].passage} [1]", True


async def _openai(url: str, key: str, model: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {key}"}, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1})
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
