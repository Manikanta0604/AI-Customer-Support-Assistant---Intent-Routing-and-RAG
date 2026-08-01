import io
import re
import uuid
from pathlib import Path
from docx import Document
from pypdf import PdfReader
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from .config import Settings
from .schemas import Citation


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    if suffix == ".docx":
        return "\n".join(p.text for p in Document(io.BytesIO(content)).paragraphs)
    if suffix in {".md", ".markdown", ".txt"}:
        return content.decode("utf-8", errors="replace")
    raise ValueError("Supported types: PDF, DOCX, Markdown, and TXT")


def chunk_markdown(text: str, size: int = 900) -> list[tuple[str | None, str]]:
    section: str | None = None
    pieces: list[tuple[str | None, str]] = []
    buffer = ""
    for line in text.splitlines():
        if line.startswith("#"):
            if buffer.strip():
                pieces.extend(_split(section, buffer, size))
            section, buffer = line.lstrip("# ").strip(), ""
        else:
            buffer += " " + line.strip()
    if buffer.strip():
        pieces.extend(_split(section, buffer, size))
    return pieces


def _split(section: str | None, text: str, size: int) -> list[tuple[str | None, str]]:
    clean = re.sub(r"\s+", " ", text).strip()
    return [(section, clean[i:i + size]) for i in range(0, len(clean), size) if clean[i:i + size].strip()]


class KnowledgeStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = QdrantClient(url=settings.qdrant_url)
        self.encoder = SentenceTransformer(settings.embedding_model)
        size = self.encoder.get_sentence_embedding_dimension()
        if not self.client.collection_exists(settings.collection_name):
            self.client.create_collection(settings.collection_name, vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE))

    def index(self, source: str, text: str) -> int:
        chunks = chunk_markdown(text)
        vectors = self.encoder.encode([chunk for _, chunk in chunks], normalize_embeddings=True)
        self.client.upsert(
            self.settings.collection_name,
            points=[models.PointStruct(id=str(uuid.uuid4()), vector=vector.tolist(), payload={"source": source, "section": section, "passage": chunk}) for vector, (section, chunk) in zip(vectors, chunks)],
            wait=True,
        )
        return len(chunks)

    def search(self, query: str, limit: int = 4) -> list[Citation]:
        vector = self.encoder.encode(query, normalize_embeddings=True).tolist()
        points = self.client.query_points(self.settings.collection_name, query=vector, limit=limit).points
        return [Citation(**point.payload, score=round(float(point.score), 4)) for point in points]

    def is_empty(self) -> bool:
        return self.client.count(self.settings.collection_name, exact=True).count == 0
