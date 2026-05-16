# Secure Chat Portal (FastAPI + Groq + Auth)

Small FastAPI project with:
- Public health check: `GET /ping`
- Local API-key protected chat: `POST /chat` (header `X-API-Key`)
- JWT auth: `POST /auth/register`, `POST /auth/login`
- JWT-protected chat: `POST /chat2` (header `Authorization: Bearer <token>`)
- JWT-protected chat history: `POST /chat/history`

## Requirements

Python 3.10+ recommended.

Install dependencies:

```bash
pip install fastapi uvicorn python-dotenv langchain-groq groq python-jose[cryptography] passlib
```

## Environment

Copy `.env.example` to `.env` in the project folder:

```bash
copy .env.example .env
```

Then edit `.env` and set your values:

```env
GROQ_API_KEY=your_groq_key_here
# Optional
GROQ_MODEL=openai/gpt-oss-20b

# Auth / JWT
SECRET_KEY=change-me
TOKEN_EXPIRE_MIN=30

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## Run

```bash
python -m uvicorn main:app --reload --port 8000
```

Open docs:
- Swagger UI: http://127.0.0.1:8000/docs

## Web UI (React)

A minimal React UI is in the `frontend/` folder.

1) Start the backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

2) Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The UI defaults to calling `http://127.0.0.1:8000`. To change it, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Endpoints

### 1) Health

```bash
curl http://127.0.0.1:8000/ping
```

### 2) Register + Login (JWT)

Register:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"u1","password":"p1"}'
```

Login (returns `access_token`):

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"u1","password":"p1"}'
```

### 3) Chat with API Key (`/chat`)

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-student-001" \
  -d '{"question":"Hello"}'
```

### 4) Chat with JWT (`/chat2`)

```bash
curl -X POST http://127.0.0.1:8000/chat2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"question":"Hello"}'
```

### 5) Chat history (`/chat/history`)

Returns the last `limit` chat entries for the authenticated user.

```bash
curl -X POST http://127.0.0.1:8000/chat/history \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"limit": 50}'
```

## Notes

- `users_db` and `chat_history_db` are in-memory, so they reset when you restart the server.
- If Groq returns `401 invalid_api_key`, double-check `GROQ_API_KEY` in `.env` and restart the server.
