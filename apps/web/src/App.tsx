import { BrowserRouter, Route, Routes } from 'react-router'
import { RequireAuth } from './components/RequireAuth'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Report from './pages/Report'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/app" element={<RequireAuth><Dashboard /></RequireAuth>} />
        <Route path="/app/runs/:id" element={<RequireAuth><Report /></RequireAuth>} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </BrowserRouter>
  )
}
