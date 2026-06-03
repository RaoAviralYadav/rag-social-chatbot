from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.vector_store import vector_store

from app.config import settings
from app.routers import ingest, chat

app = FastAPI(title="RAG Social Chatbot", version="0.1.0", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/health")
def health_check():
    return {"status": "ok", "version": app.version}

@app.on_event("startup")
def startup():
    vector_store.initialize()