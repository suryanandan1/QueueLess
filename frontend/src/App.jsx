import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute, { GuestRoute } from './components/ProtectedRoute';
import LoadingScreen from './components/LoadingScreen';
import { useAuth } from './hooks/useAuth';
import AuthLayout from './layouts/AuthLayout';
import DashboardLayout from './layouts/DashboardLayout';
import AccountPage from './pages/AccountPage';
import NotificationsPage from './pages/NotificationsPage';
import NotFoundPage from './pages/NotFoundPage';
import AdminDashboard from './pages/admin/AdminDashboard';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';
import AnalyticsPage from './pages/business/AnalyticsPage';
import AppointmentsManagePage from './pages/business/AppointmentsManagePage';
import BusinessOverviewPage from './pages/business/BusinessOverviewPage';
import BusinessProfilePage from './pages/business/BusinessProfilePage';
import CountersPage from './pages/business/CountersPage';
import QueueMonitorPage from './pages/business/QueueMonitorPage';
import QueuesPage from './pages/business/QueuesPage';
import ServiceManagementPage from './pages/business/ServiceManagementPage';
import BookAppointmentPage from './pages/customer/BookAppointmentPage';
import BusinessDetailsPage from './pages/customer/BusinessDetailsPage';
import CustomerDashboard from './pages/customer/CustomerDashboard';
import MyAppointmentsPage from './pages/customer/MyAppointmentsPage';
import MyTokensPage from './pages/customer/MyTokensPage';
import TokenTrackingPage from './pages/customer/TokenTrackingPage';
import OwnerDashboard from './pages/owner/OwnerDashboard';
import CounterConsolePage from './pages/staff/CounterConsolePage';
import StaffDashboard from './pages/staff/StaffDashboard';
import { HOME_PATH_BY_ROLE, ROLES } from './utils/constants';

const BUSINESS_TEAM_ROLES = [ROLES.BUSINESS_OWNER, ROLES.STAFF, ROLES.SUPER_ADMIN];

function HomeRedirect() {
  const { user, initializing } = useAuth();
  if (initializing) return <LoadingScreen fullPage />;
  return <Navigate to={user ? HOME_PATH_BY_ROLE[user.role] : '/login'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />

      <Route element={<GuestRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>
      </Route>
      {/* Reachable whether or not someone is signed in on this browser. */}
      <Route element={<AuthLayout />}>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/account" element={<AccountPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          {/* Customer flows are open to every signed-in user (staff can queue somewhere too). */}
          <Route path="/explore/businesses/:businessId" element={<BusinessDetailsPage />} />
          <Route path="/my/tokens" element={<MyTokensPage />} />
          <Route path="/my/tokens/:tokenId" element={<TokenTrackingPage />} />
          <Route path="/my/appointments" element={<MyAppointmentsPage />} />
          <Route path="/book/:serviceId" element={<BookAppointmentPage />} />

          <Route element={<ProtectedRoute roles={[ROLES.CUSTOMER]} />}>
            <Route path="/customer" element={<CustomerDashboard />} />
          </Route>
          <Route element={<ProtectedRoute roles={[ROLES.BUSINESS_OWNER]} />}>
            <Route path="/owner" element={<OwnerDashboard />} />
          </Route>
          <Route element={<ProtectedRoute roles={[ROLES.STAFF]} />}>
            <Route path="/staff" element={<StaffDashboard />} />
          </Route>
          <Route element={<ProtectedRoute roles={[ROLES.SUPER_ADMIN]} />}>
            <Route path="/admin" element={<AdminDashboard />} />
          </Route>
          <Route element={<ProtectedRoute roles={BUSINESS_TEAM_ROLES} />}>
            <Route path="/businesses/:businessId" element={<Navigate to="overview" replace />} />
            <Route path="/businesses/:businessId/overview" element={<BusinessOverviewPage />} />
            <Route path="/businesses/:businessId/queues" element={<QueuesPage />} />
            <Route path="/businesses/:businessId/queues/:queueId" element={<QueueMonitorPage />} />
            <Route path="/businesses/:businessId/appointments" element={<AppointmentsManagePage />} />
            <Route path="/businesses/:businessId/services" element={<ServiceManagementPage />} />
            <Route path="/businesses/:businessId/counters" element={<CountersPage />} />
            <Route path="/businesses/:businessId/profile" element={<BusinessProfilePage />} />
            <Route path="/businesses/:businessId/analytics" element={<AnalyticsPage />} />
            <Route path="/counters/:counterId/console" element={<CounterConsolePage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
