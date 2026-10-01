import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useSession } from '../lib/auth'
import { loginErrorCode } from '../lib/loginErrors'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { loading, session } = useSession()
  const location = useLocation()
  const error = loginErrorCode(location.search, location.hash)
  if (loading) return <div role="status" aria-label="Checking your session" className="min-h-[100dvh] bg-bg" />
  if (error) return <Navigate to={`/login?auth_error=${error}`} replace />
  if (!session) return <Navigate to="/login" replace />
  return children
}
