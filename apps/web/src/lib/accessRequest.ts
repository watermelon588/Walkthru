export type AccessRequestRow = { id: string; plan: string; note: string; status: string; created_at: string }

/** After an ambiguous response, read saved state once. Never repeat the mutation automatically. */
export async function confirmedAccessRequest<T extends { id: string }>(
  create: () => Promise<T>, read: () => Promise<{ requests: AccessRequestRow[] }>,
  sameAccount: () => Promise<boolean>, plan: string, note: string,
): Promise<T | AccessRequestRow> {
  const started = Date.now()
  try { return await create() }
  catch (original) {
    if (!await sameAccount()) throw new Error('Your account changed. Check requests from the original account before trying again.')
    let saved: { requests: AccessRequestRow[] }
    try { saved = await read() }
    catch {
      throw new Error('Could not confirm whether your request was saved. Reload Plan & billing and check its status before sending again.')
    }
    if (!await sameAccount()) throw new Error('Your account changed. Check requests from the original account before trying again.')
    const request = saved.requests.find((r) => r.plan === plan && r.note === note
      && (r.status === 'pending' || Date.parse(r.created_at) >= started - 5000))
    if (request) return request
    throw original
  }
}
