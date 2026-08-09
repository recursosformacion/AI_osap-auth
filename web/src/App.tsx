import { Navigate, Route, Routes } from 'react-router-dom'

import { AccountLayout } from './components/AccountLayout'
import { AccountPage } from './pages/Account/AccountPage'
import { AdminUsersPage } from './pages/AdminUsers/AdminUsersPage'
import { ChangeEmailPage } from './pages/ChangeEmail/ChangeEmailPage'
import { ChangePasswordPage } from './pages/ChangePassword/ChangePasswordPage'
import { DeleteAccountPage } from './pages/DeleteAccount/DeleteAccountPage'
import { ForgotPasswordPage } from './pages/ForgotPassword/ForgotPasswordPage'
import { LoginPage } from './pages/Login/LoginPage'
import { LogoutPage } from './pages/Logout/LogoutPage'
import { RegisterPage } from './pages/Register/RegisterPage'
import { ResetPasswordPage } from './pages/ResetPassword/ResetPasswordPage'
import { SessionsPage } from './pages/Sessions/SessionsPage'
import { VerifyEmailPage } from './pages/VerifyEmail/VerifyEmailPage'
import { AdminRoute } from './routes/AdminRoute'
import { ProtectedRoute } from './routes/ProtectedRoute'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/auth/login" replace />} />

      {/* Rutas públicas */}
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<RegisterPage />} />
      <Route path="/auth/verify-email" element={<VerifyEmailPage />} />
      <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
      <Route path="/auth/logout" element={<LogoutPage />} />

      {/* Área de cuenta (protegida) */}
      <Route
        path="/auth/account"
        element={
          <ProtectedRoute>
            <AccountLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AccountPage />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="password" element={<ChangePasswordPage />} />
        <Route path="email" element={<ChangeEmailPage />} />
        <Route path="delete" element={<DeleteAccountPage />} />
      </Route>

      {/* Administración (rol admin, según backend) */}
      <Route
        path="/auth/admin/users"
        element={
          <AdminRoute>
            <AccountLayout>
              <AdminUsersPage />
            </AccountLayout>
          </AdminRoute>
        }
      />

      <Route path="*" element={<Navigate to="/auth/login" replace />} />
    </Routes>
  )
}
