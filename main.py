import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from groq import AuthenticationError as GroqAuthenticationError

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# Load environment variables from .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Initialized once — reused by all routes (when configured)
groq_llm = None
if GROQ_API_KEY:
    groq_llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=512,
        api_key=GROQ_API_KEY,
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


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    system_prompt: str = Field(
        default="You are a helpful and concise AI assistant.",
        description="System instruction for the model"
    )


class ChatResponse(BaseModel):
    answer: str
    model: str
    tokens_used: int
    authenticated_as: str


@app.post("/chat", response_model=ChatResponse, tags=["AI — Protected"])
async def chat(
    req: ChatRequest,
    username: str = Depends(require_api_key),  # security injected here
):
    if groq_llm is None:
        raise HTTPException(
            status_code=503,
            detail="Server is missing GROQ_API_KEY. Add GROQ_API_KEY to your .env and restart the server.",
        )
    # Build LangChain messages — same pattern as the base script
    messages = [
        SystemMessage(content=req.system_prompt),
        HumanMessage(content=req.question),
    ]
    # Call the Groq model
    try:
        response = groq_llm.invoke(messages)
    except GroqAuthenticationError:
        raise HTTPException(
            status_code=502,
            detail=(
                "Groq rejected GROQ_API_KEY (401 invalid_api_key). "
                "Double-check the key value in .env and restart the server."
            ),
        )
    # Extract token usage metadata
    usage = response.usage_metadata or {}
    tokens = usage.get("total_tokens", 5)
    return ChatResponse(
        answer=response.content,
        model=GROQ_MODEL,
        tokens_used=tokens,
        authenticated_as=username,
    )
