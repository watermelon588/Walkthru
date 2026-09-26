import { lazy, Suspense, useEffect, type ComponentType } from 'react'
import { BrowserRouter, Route, Routes, useLocation } from 'react-router'
import { Toaster } from './components/Toaster'
import { NotificationsProvider } from './components/NotificationsProvider'
import Landing from './pages/Landing'

// Landing is the LCP path, so it ships in the main bundle. Everything else loads on demand.

/** A lazy page that survives a stale bundle: after a deploy (or a renamed file in dev) the old chunk is gone, the
 *  import fails and React would show a blank page. Reload once to fetch the current version; a second failure is real. */
function page<T extends ComponentType<any>>(load: () => Promise<{ default: T }>) { // any: React.lazy's own constraint
  return lazy(async () => {
    try {
      const mod = await load()
      try { sessionStorage.removeItem(RELOADED) } catch { /* storage can be blocked */ }
      return mod
    } catch (error) {
      let tried = true
      try { tried = sessionStorage.getItem(RELOADED) === '1'; sessionStorage.setItem(RELOADED, '1') } catch { /* no storage: never loop */ }
      if (!tried) window.location.reload()
      throw error
    }
  })
}
const RELOADED = 'walkthru.chunk-reload'
const RequireAuth = page(() => import('./components/RequireAuth').then((m) => ({ default: m.RequireAuth })))
const Dashboard = page(() => import('./pages/Dashboard'))
const AgentLab = page(() => import('./pages/AgentLab'))
const Login = page(() => import('./pages/Login'))
const Public = page(() => import('./pages/Public'))
const Report = page(() => import('./pages/Report'))
const Settings = page(() => import('./pages/Settings'))
const Feedback = page(() => import('./pages/Feedback'))
const Bot = page(() => import('./pages/Bot'))
const Billing = page(() => import('./pages/Billing'))
const Mcp = page(() => import('./pages/Mcp'))
const Watch = page(() => import('./pages/Watch'))
const Compare = page(() => import('./pages/Compare'))
const Teams = page(() => import('./pages/Teams'))
const Team = page(() => import('./pages/Team'))
const TeamReport = page(() => import('./pages/TeamReport'))
const Join = page(() => import('./pages/Join'))
const CompareResult = page(() => import('./pages/Compare').then((m) => ({ default: m.CompareResult })))
const Docs = page(() => import('./pages/Docs'))
const Privacy = page(() => import('./pages/Privacy'))
const Terms = page(() => import('./pages/Terms'))
const Security = page(() => import('./pages/Security'))
const NotFound = page(() => import('./pages/NotFound'))

/** New page: start at the top. With a #hash: scroll to it once the (lazy) page has rendered it. */
function ScrollManager() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (!hash) {
      window.scrollTo(0, 0)
      return
    }
    const id = decodeURIComponent(hash.slice(1))
    let frame = 0
    let tries = 0
    const find = () => {
      const el = document.getElementById(id)
      if (el) el.scrollIntoView()
      else if (tries++ < 90) frame = requestAnimationFrame(find)
    }
    find()
    return () => cancelAnimationFrame(frame)
  }, [pathname, hash])
  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollManager />
      <NotificationsProvider>
        <Toaster />
        <Suspense fallback={<div role="status" aria-label="Loading" className="min-h-[100dvh] bg-bg" />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/agent-lab" element={<AgentLab />} />
            <Route path="/login" element={<Login />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/bot" element={<Bot />} />
            <Route path="/security" element={<Security />} />
            <Route path="/app" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="/app/settings" element={<RequireAuth><Settings /></RequireAuth>} />
            <Route path="/app/feedback" element={<RequireAuth><Feedback /></RequireAuth>} />
            <Route path="/app/billing" element={<RequireAuth><Billing /></RequireAuth>} />
            <Route path="/app/mcp" element={<RequireAuth><Mcp /></RequireAuth>} />
            <Route path="/app/watch" element={<RequireAuth><Watch /></RequireAuth>} />
            <Route path="/app/compare" element={<RequireAuth><Compare /></RequireAuth>} />
            <Route path="/app/compare/:id" element={<RequireAuth><CompareResult /></RequireAuth>} />
            <Route path="/app/runs/:id" element={<RequireAuth><Report /></RequireAuth>} />
            <Route path="/app/team" element={<RequireAuth><Teams /></RequireAuth>} />
            <Route path="/app/team/:id/runs/:runId" element={<RequireAuth><TeamReport /></RequireAuth>} />
            <Route path="/app/team/:id/:tab?" element={<RequireAuth><Team /></RequireAuth>} />
            <Route path="/join" element={<Join />} />
            <Route path="/r/:id" element={<Public />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </NotificationsProvider>
    </BrowserRouter>
  )
}
