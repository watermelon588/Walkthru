/** Keep callback secrets and provider-supplied text out of the rendered error and redirect URL. */
export function loginError(search: string, hash: string): string | null {
  const query = new URLSearchParams(search)
  const fragment = new URLSearchParams(hash.replace(/^#/, ''))
  const code = query.get('auth_error') ?? fragment.get('error_code') ?? query.get('error_code')
    ?? fragment.get('error') ?? query.get('error')
  if (!code) return null
  if (code === 'otp_expired') return 'That sign-in link is invalid or expired. Request a new link and open the newest email.'
  if (code === 'access_denied') return 'Sign-in was cancelled or refused. You can try again or use an email link.'
  return 'Sign-in could not be completed. Try again or request a new email link.'
}

export function loginErrorCode(search: string, hash: string): string | null {
  if (!loginError(search, hash)) return null
  const values = new URLSearchParams(`${search.replace(/^\?/, '')}&${hash.replace(/^#/, '')}`)
  const code = values.get('error_code') ?? values.get('error')
  return code === 'otp_expired' || code === 'access_denied' ? code : 'callback_failed'
}

export function inviteCode(hash: string): string {
  try { return decodeURIComponent(hash.replace(/^#/, '')).trim() }
  catch { return '' } // a malformed pasted URL must never crash the invitation page
}
