import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useSession } from '../lib/auth'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { loading, session } = useSession()
  if (loading) return <div role="status" aria-label="Checking your session" className="min-h-[100dvh] bg-bg" />
  if (!session) return <Navigate to="/login" replace />
  return children
}
