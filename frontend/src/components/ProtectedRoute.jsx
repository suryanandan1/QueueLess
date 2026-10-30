import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { HOME_PATH_BY_ROLE } from '../utils/constants';
import LoadingScreen from './LoadingScreen';

/** Requires a signed-in user; optionally restricts to specific platform roles. */
export default function ProtectedRoute({ roles }) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <LoadingScreen fullPage message="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={HOME_PATH_BY_ROLE[user.role] ?? '/'} replace />;
  }
  return <Outlet />;
}

/** For login/register pages: signed-in users are sent to their dashboard. */
export function GuestRoute() {
  const { user, initializing } = useAuth();
  if (initializing) return <LoadingScreen fullPage message="Checking your session…" />;
  if (user) return <Navigate to={HOME_PATH_BY_ROLE[user.role] ?? '/'} replace />;
  return <Outlet />;
}
