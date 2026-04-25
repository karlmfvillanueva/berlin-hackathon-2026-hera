import { createBrowserRouter } from "react-router-dom"
import App from "./App"
import { Login } from "./auth/pages/Login"
import { Signup } from "./auth/pages/Signup"
import { ProtectedRoute } from "./auth/ProtectedRoute"
import { Dashboard } from "./pages/Dashboard"
import { VideoDetail } from "./pages/VideoDetail"

export const router = createBrowserRouter([
  { path: "/", element: <App /> },
  { path: "/login", element: <Login /> },
  { path: "/signup", element: <Signup /> },
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
