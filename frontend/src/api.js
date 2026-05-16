const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, { method = 'GET', token, json } = {}) {
    const headers = {}
    if (json !== undefined) headers['Content-Type'] = 'application/json'
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: json !== undefined ? JSON.stringify(json) : undefined,
    })

    const contentType = res.headers.get('content-type') || ''
    const isJson = contentType.includes('application/json')
    const body = isJson ? await res.json() : await res.text()

    if (!res.ok) {
        const detail = isJson && body && body.detail ? body.detail : JSON.stringify(body)
        throw new Error(`${res.status} ${res.statusText}: ${detail}`)
    }

    return body
}

export async function ping() {
    return request('/ping')
}

export async function register(username, password) {
    return request('/auth/register', {
        method: 'POST',
        json: { username, password },
    })
}

export async function login(username, password) {
    return request('/auth/login', {
        method: 'POST',
        json: { username, password },
    })
}

export async function chat(token, question, system_prompt) {
    return request('/chat2', {
        method: 'POST',
        token,
        json: {
            question,
            ...(system_prompt ? { system_prompt } : {}),
        },
    })
}

export async function history(token, limit = 50) {
    return request('/chat/history', {
        method: 'POST',
        token,
        json: { limit },
    })
}
