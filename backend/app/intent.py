import re
from dataclasses import dataclass
from .schemas import Intent


INTENT_TERMS: dict[Intent, set[str]] = {
    "billing": {"bill", "billing", "charge", "charged", "refund", "payment", "invoice", "subscription", "cancel"},
    "technical": {"error", "broken", "bug", "crash", "loading", "install", "connection", "service", "technical"},
    "account": {"account", "login", "password", "signin", "sign-in", "locked", "security", "compromised"},
    "product": {"feature", "product", "plan", "price", "pricing", "available", "delivery", "order", "tracking"},
    "complaint": {"complaint", "unhappy", "terrible", "awful", "angry", "disappointed", "unacceptable"},
    "general": set(),
}

URGENT_TERMS = {
    "fraud", "stolen", "compromised", "lawyer", "legal action", "emergency",
    "unsafe", "security breach", "human", "representative", "agent", "supervisor",
}


@dataclass
class Route:
    intent: Intent
    confidence: float
    urgent_reason: str | None = None


def route_intent(message: str) -> Route:
    lowered = message.lower()
    for phrase in URGENT_TERMS:
        if phrase in lowered:
            intent: Intent = "account" if phrase in {"fraud", "stolen", "compromised", "security breach"} else "complaint"
            return Route(intent, 0.99, f"Sensitive or human-request keyword: {phrase}")
    words = set(re.findall(r"[a-z]+(?:-[a-z]+)?", lowered))
    scores = {intent: len(words & terms) for intent, terms in INTENT_TERMS.items() if intent != "general"}
    best = max(scores, key=scores.get) if any(scores.values()) else "general"
    matches = scores.get(best, 0)
    confidence = min(0.55 + matches * 0.15, 0.95) if matches else 0.5
    return Route(best, confidence)
