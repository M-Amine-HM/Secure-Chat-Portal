import React, { useEffect, useMemo, useState } from 'react'
import * as api from './api'

const TOKEN_KEY = 'secure_chat_portal_token'
const CHATLOG_KEY = 'secure_chat_portal_chatlog'

function safeJsonParse(value) {
    try {
        return JSON.parse(value)
    } catch {
        return null
    }
}

export default function App() {
    const [mode, setMode] = useState('login') // 'login' | 'register'
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')

    const [token, setToken] = useState(() => {
        const raw = localStorage.getItem(TOKEN_KEY)
        return raw ? raw : ''
    })

    const [authError, setAuthError] = useState('')
    const [authBusy, setAuthBusy] = useState(false)

    const [question, setQuestion] = useState('')
    const [systemPrompt, setSystemPrompt] = useState('')
    const [chatBusy, setChatBusy] = useState(false)
    const [chatError, setChatError] = useState('')

    const [chatLog, setChatLog] = useState(() => {
        // Local-only chat log for this browser session
        const saved = safeJsonParse(sessionStorage.getItem(CHATLOG_KEY) || '')
        return Array.isArray(saved) ? saved : []
    })

    useEffect(() => {
        sessionStorage.setItem(CHATLOG_KEY, JSON.stringify(chatLog))
    }, [chatLog])

    const isAuthed = useMemo(() => Boolean(token), [token])

    async function onRegisterOrLogin(e) {
        e.preventDefault()
        setAuthError('')
        setChatError('')

        if (!username.trim() || !password) {
            setAuthError('Username and password are required.')
            return
        }

        setAuthBusy(true)
        try {
            if (mode === 'register') {
                await api.register(username.trim(), password)
                // After successful register, switch to login
                setMode('login')
            } else {
                const res = await api.login(username.trim(), password)
                const newToken = res.access_token
                setToken(newToken)
                localStorage.setItem(TOKEN_KEY, newToken)
            }
        } catch (err) {
            setAuthError(err instanceof Error ? err.message : String(err))
        } finally {
            setAuthBusy(false)
        }
    }

    function logout() {
        setToken('')
        localStorage.removeItem(TOKEN_KEY)
    }

    async function sendChat(e) {
        e.preventDefault()
        setChatError('')

        if (!question.trim()) {
            setChatError('Write a question first.')
            return
        }

        setChatBusy(true)
        const q = question.trim()
        setQuestion('')

        setChatLog((prev) => [...prev, { role: 'user', text: q }])

        try {
            const res = await api.chat(token, q, systemPrompt.trim() || undefined)
            setChatLog((prev) => [
                ...prev,
                {
                    role: 'ai',
                    text: res.answer,
                    meta: `${res.model} · tokens ${res.tokens_used} · as ${res.authenticated_as}`,
                },
            ])
        } catch (err) {
            setChatError(err instanceof Error ? err.message : String(err))
            // Put the question back if it failed
            setChatLog((prev) => prev.slice(0, -1))
            setQuestion(q)
        } finally {
            setChatBusy(false)
        }
    }

    async function loadHistory() {
        setChatError('')
        setChatBusy(true)
        try {
            const res = await api.history(token, 50)
            // Convert server history to local log format (most recent last)
            const items = (res.history || []).map((h) => [
                { role: 'user', text: h.question },
                { role: 'ai', text: h.answer, meta: `${h.model || ''} · ${h.ts || ''}`.trim() },
            ])
            const flattened = items.flat()
            setChatLog(flattened)
        } catch (err) {
            setChatError(err instanceof Error ? err.message : String(err))
        } finally {
            setChatBusy(false)
        }
    }

    return (
        <div className="container">
            <div className="topbar">
                <h1>Secure Chat Portal</h1>
                <div className="row">
                    {isAuthed ? (
                        <>
                            <span className="small">Logged in</span>
                            <button onClick={logout}>Logout</button>
                        </>
                    ) : (
                        <span className="small">Not logged in</span>
                    )}
                </div>
            </div>

            {!isAuthed ? (
                <div className="card">
                    <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                        <div className="row">
                            <button
                                className={mode === 'login' ? 'primary' : ''}
                                onClick={() => setMode('login')}
                                type="button"
                            >
                                Login
                            </button>
                            <button
                                className={mode === 'register' ? 'primary' : ''}
                                onClick={() => setMode('register')}
                                type="button"
                            >
                                Register
                            </button>
                        </div>
                        <span className="small">Uses /auth/register and /auth/login</span>
                    </div>

                    <form onSubmit={onRegisterOrLogin} style={{ marginTop: 12 }}>
                        <div className="row">
                            <div style={{ flex: 1, minWidth: 220 }}>
                                <label>Username</label>
                                <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
                            </div>
                            <div style={{ flex: 1, minWidth: 220 }}>
                                <label>Password</label>
                                <input
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    type="password"
                                    autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                                />
                            </div>
                        </div>

                        {authError ? <div className="error" style={{ marginTop: 10 }}>{authError}</div> : null}

                        <div className="row" style={{ marginTop: 12, alignItems: 'center' }}>
                            <button className="primary" disabled={authBusy}>
                                {authBusy ? 'Working…' : mode === 'register' ? 'Create account' : 'Login'}
                            </button>
                            {mode === 'register' ? (
                                <span className="small">After register, login to chat.</span>
                            ) : (
                                <span className="small">You’ll get a JWT access token.</span>
                            )}
                        </div>
                    </form>
                </div>
            ) : (
                <div className="card">
                    <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div className="small">Chat (JWT) → POST /chat2</div>
                            <div className="small">History → POST /chat/history</div>
                        </div>
                        <div className="row">
                            <button onClick={loadHistory} disabled={chatBusy}>
                                Load history
                            </button>
                            <button
                                onClick={() => {
                                    setChatLog([])
                                    sessionStorage.removeItem(CHATLOG_KEY)
                                }}
                                disabled={chatBusy}
                            >
                                Clear local
                            </button>
                        </div>
                    </div>

                    <form onSubmit={sendChat} style={{ marginTop: 12 }}>
                        <div className="row">
                            <div style={{ flex: 1, minWidth: 320 }}>
                                <label>Question</label>
                                <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
                            </div>
                            <div style={{ flex: 1, minWidth: 320 }}>
                                <label>System prompt (optional)</label>
                                <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} />
                            </div>
                        </div>

                        {chatError ? <div className="error" style={{ marginTop: 10 }}>{chatError}</div> : null}

                        <div className="row" style={{ marginTop: 12, alignItems: 'center' }}>
                            <button className="primary" disabled={chatBusy}>
                                {chatBusy ? 'Sending…' : 'Send'}
                            </button>
                            <span className="small">Token stored in localStorage.</span>
                        </div>
                    </form>

                    <div className="chatLog">
                        {chatLog.length === 0 ? (
                            <div className="small" style={{ marginTop: 12 }}>No messages yet.</div>
                        ) : (
                            chatLog.map((m, idx) => (
                                <div key={idx} className={`bubble ${m.role === 'user' ? 'user' : 'ai'}`}>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                                    {m.meta ? <div className="small" style={{ marginTop: 6 }}>{m.meta}</div> : null}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
