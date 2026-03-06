"""
Jarvis-MCP — FastAPI entry point
OpenAI-compatible API server
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from src.auth.middleware import verify_api_key
from src.agent.core import AgentCore
from src.memory.store import MemoryStore

app = FastAPI(title="Jarvis-MCP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = MemoryStore()
agent = AgentCore(memory=memory)


# ── OpenAI-compatible schemas ──────────────────────────────────────────────

class Message(BaseModel):
    role: str  # system | user | assistant | tool
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "jarvis"
    messages: List[Message]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    conversation_id: Optional[str] = None  # para memoria persistente


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list
    usage: dict


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/v1/models")
async def list_models(_: str = Depends(verify_api_key)):
    return {
        "object": "list",
        "data": [
            {"id": "jarvis", "object": "model", "owned_by": "local"},
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    _: str = Depends(verify_api_key)
):
    response = await agent.run(
        messages=[m.dict() for m in request.messages],
        conversation_id=request.conversation_id,
        temperature=request.temperature,
    )
    return response


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
