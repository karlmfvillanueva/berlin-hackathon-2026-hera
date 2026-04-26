import { createBrowserRouter } from "react-router-dom"
import { Login } from "./auth/pages/Login"
import { Signup } from "./auth/pages/Signup"
import { ProtectedRoute } from "./auth/ProtectedRoute"
import { AgentApp } from "./pages/AgentApp"
import { Dashboard } from "./pages/Dashboard"
import { Datenschutz } from "./pages/Datenschutz"
import { Impressum } from "./pages/Impressum"
import { Landing } from "./pages/Landing"
import { VideoDetail } from "./pages/VideoDetail"

export const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/app", element: <AgentApp /> },
  { path: "/login", element: <Login /> },
  { path: "/signup", element: <Signup /> },
  { path: "/impressum", element: <Impressum /> },
  { path: "/datenschutz", element: <Datenschutz /> },
  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },
  {
    path: "/dashboard/v/:id",
    element: (
      <ProtectedRoute>
        <VideoDetail />
      </ProtectedRoute>
    ),
  },
])
