import Landing from './pages/Landing'
import Login from './pages/Login'

// Two pages don't need a router. Add react-router when the dashboard (T10) brings nested routes.
export default function App() {
  return location.pathname.startsWith('/login') ? <Login /> : <Landing />
}
