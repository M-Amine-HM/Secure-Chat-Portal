import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# Load environment variables from .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialized once — reused by all routes
groq_llm = ChatGroq(
    model="grok-4.20-reasoning",
    temperature=0,
    max_tokens=512,
    api_key=GROQ_API_KEY
)
app = FastAPI(
    title="Groq LLM API — AI Lab",
    description="Secured FastAPI for Groq grok-4.20-reasoning consumption.",
    version="1.0.0",
)


@app.get("/ping", tags=["Public"])
async def ping():
    return {"status": "ok", "message": "Groq API is running."}

VALID_API_KEYS: dict[str, str] = {
    "sk-student-001": "student_a",
    "sk-student-002": "student_b",
    "sk-admin-999": "admin",
}


def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401,
                            detail="Invalid API key.")
    return VALID_API_KEYS[x_api_key]  # ← e.g. 'student_a'
