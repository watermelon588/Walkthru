import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Route, Routes, useLocation } from 'react-router'
import Landing from './pages/Landing'

// Landing is the LCP path, so it ships in the main bundle. Everything else loads on demand.
const RequireAuth = lazy(() => import('./components/RequireAuth').then((m) => ({ default: m.RequireAuth })))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const AgentLab = lazy(() => import('./pages/AgentLab'))
const Login = lazy(() => import('./pages/Login'))
const Public = lazy(() => import('./pages/Public'))
const Report = lazy(() => import('./pages/Report'))
const Settings = lazy(() => import('./pages/Settings'))
const Feedback = lazy(() => import('./pages/Feedback'))
const Billing = lazy(() => import('./pages/Billing'))
const Mcp = lazy(() => import('./pages/Mcp'))
const Watch = lazy(() => import('./pages/Watch'))
const Compare = lazy(() => import('./pages/Compare'))
const Teams = lazy(() => import('./pages/Teams'))
const Team = lazy(() => import('./pages/Team'))
const TeamReport = lazy(() => import('./pages/TeamReport'))
const Join = lazy(() => import('./pages/Join'))
const CompareResult = lazy(() => import('./pages/Compare').then((m) => ({ default: m.CompareResult })))
const Docs = lazy(() => import('./pages/Docs'))
const Privacy = lazy(() => import('./pages/Privacy'))
const Terms = lazy(() => import('./pages/Terms'))
const Security = lazy(() => import('./pages/Security'))
const NotFound = lazy(() => import('./pages/NotFound'))

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
      <Suspense fallback={<div role="status" aria-label="Loading" className="min-h-[100dvh] bg-bg" />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/agent-lab" element={<AgentLab />} />
          <Route path="/login" element={<Login />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
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
    </BrowserRouter>
  )
}
