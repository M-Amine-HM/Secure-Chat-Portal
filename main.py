import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from groq import AuthenticationError as GroqAuthenticationError

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext


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


# JWT settings — store SECRET_KEY in .env for production
SECRET_KEY = "change-this-in-production-long-random-string"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MIN = 30
# Password hashing (PBKDF2 avoids bcrypt backend/version issues)
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# In-memory user store — use a real database in production
users_db: dict[str, dict] = {}
# In-memory chat history — keyed by username
chat_history_db: dict[str, list[dict]] = {}
bearer_scheme = HTTPBearer()


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MIN)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')


def require_jwt(credentials=Depends(bearer_scheme)) -> dict:
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    if not username or username not in users_db:
        raise HTTPException(status_code=401, detail="User not found.")
    return payload


class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/register", status_code=201, tags=["Auth"])
async def register(req: AuthRequest):
    if req.username in users_db:
        raise HTTPException(409, detail="Username already taken.")
    users_db[req.username] = {"hashed_password": pwd_ctx.hash(req.password)}
    return {"message": f'User {req.username!r} created.'}


@app.post("/auth/login", tags=["Auth"])
async def login(req: AuthRequest):
    user = users_db.get(req.username)
    if not user or not pwd_ctx.verify(req.password, user["hashed_password"]):
        raise HTTPException(401, detail="Incorrect credentials.")
    token = create_token({"sub": req.username})
    return {"access_token": token, "token_type": "bearer"}


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


class ChatHistoryRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


class ChatHistoryResponse(BaseModel):
    authenticated_as: str
    count: int
    history: list[dict]


@app.post("/chat", response_model=ChatResponse, tags=["AI — Protected"])
async def chat_api_key(
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

    chat_history_db.setdefault(username, []).append(
        {
            "ts": datetime.utcnow().isoformat() + "Z",
            "question": req.question,
            "answer": response.content,
            "model": GROQ_MODEL,
        }
    )
    return ChatResponse(
        answer=response.content,
        model=GROQ_MODEL,
        tokens_used=tokens,
        authenticated_as=username,
    )


@app.post("/chat2", response_model=ChatResponse, tags=["AI — Protected"])
async def chat_jwt(
    req: ChatRequest,
    payload: dict = Depends(require_jwt),  # security injected here
):
    username = payload["sub"]
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

    chat_history_db.setdefault(username, []).append(
        {
            "ts": datetime.utcnow().isoformat() + "Z",
            "question": req.question,
            "answer": response.content,
            "model": GROQ_MODEL,
        }
    )
    return ChatResponse(
        answer=response.content,
        model=GROQ_MODEL,
        tokens_used=tokens,
        authenticated_as=username,
    )


@app.post("/chat/history", response_model=ChatHistoryResponse, tags=["AI — Protected"])
async def chat_history(
    body: ChatHistoryRequest = ChatHistoryRequest(),
    payload: dict = Depends(require_jwt),
):
    username = payload["sub"]
    history = chat_history_db.get(username, [])
    sliced = history[-body.limit:]
    return ChatHistoryResponse(
        authenticated_as=username,
        count=len(sliced),
        history=sliced,
    )
