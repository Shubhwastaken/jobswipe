import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Navbar from './components/Navbar'

// New Admin Pages
import AdminDashboard from './pages/AdminDashboard'
import StudentsPage from './pages/StudentsPage'
import CompaniesPage from './pages/CompaniesPage'
import EligibilityEngine from './pages/EligibilityEngine'

import LoginPage from './pages/LoginPage'

function AdminRoute({ children }: { children: JSX.Element }) {
  const role = useAuthStore((s) => s.userRole)
  // For this MVP, we default to admin and restrict access to the placement system
  if (role !== 'admin') return <Navigate to="/login" />
  return (
    <div>
      <Navbar />
      <div style={{ padding: '24px 0' }}>
        {children}
      </div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Redirect root to Admin Dashboard since this is primarily an admin tool now */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        {/* Public Route */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Admin Routes */}
        <Route path="/dashboard" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
        <Route path="/students" element={<AdminRoute><StudentsPage /></AdminRoute>} />
        <Route path="/companies" element={<AdminRoute><CompaniesPage /></AdminRoute>} />
        <Route path="/eligibility" element={<AdminRoute><EligibilityEngine /></AdminRoute>} />
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  )
}

export default App
