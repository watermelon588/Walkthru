/** Keep API messages readable and include a server-generated support reference. */
export async function apiError(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({})) as { detail?: unknown } | null
  const message = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`
  const id = response.headers.get('X-Request-Id')
  return /^[a-f0-9]{32}$/.test(id ?? '') ? `${message} Reference: ${id}.` : message
}
