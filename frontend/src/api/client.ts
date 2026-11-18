const BASE_URL = import.meta.env.VITE_API_BASE_URL
const CSRF_COOKIE_NAME = 'csrf_token'
const CSRF_HEADER_NAME = 'X-CSRF-Token'
const MUTATING_METHODS = new Set(['POST', 'PATCH', 'PUT', 'DELETE'])

export class ApiError extends Error {
  status: number
  detail: string

  constructor (status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

function readCsrfCookie (): string | undefined {
  return document.cookie
    .split('; ')
    .find(entry => entry.startsWith(`${CSRF_COOKIE_NAME}=`))
    ?.split('=', 2)[1]
}

export async function apiFetch<T> (path: string, options: { method?: string, body?: unknown } = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = {}

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (MUTATING_METHODS.has(method)) {
    const csrfToken = readCsrfCookie()
    if (csrfToken) {
      headers[CSRF_HEADER_NAME] = csrfToken
    }
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return await response.json() as T
}
