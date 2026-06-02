# RAG Social Chatbot

Full-stack RAG chatbot that ingests YouTube + Instagram Reels, computes engagement metrics,
and lets creators ask comparative questions via a streaming chat interface.

## Stack
- **Frontend**: Next.js 14
- **Backend**: FastAPI
- **Orchestration**: LangChain
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: ChromaDB (dev) / Qdrant (prod)
- **LLM**: GPT-4o-mini

## Setup
See installation steps in each subdirectory.

## Env Vars
- Copy `backend/.env.example` → `backend/.env`
- Copy `frontend/.env.local.example` → `frontend/.env.local`