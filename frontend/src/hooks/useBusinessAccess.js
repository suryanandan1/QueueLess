import { useAsync } from './useAsync';
import { useAuth } from './useAuth';
import { businessApi } from '../services/businessApi';
import { MEMBER_ROLES, ROLES } from '../utils/constants';

/**
 * Resolve what the signed-in user may do in a business. This only drives the UI;
 * the backend independently enforces every permission.
 */
export function useBusinessAccess(businessId) {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === ROLES.SUPER_ADMIN;

  const { data: memberships, loading, error } = useAsync(
    () => (isSuperAdmin ? Promise.resolve([]) : businessApi.mine()),
    [isSuperAdmin],
  );

  const membership = memberships?.find((item) => item.business.id === Number(businessId));
  const role = membership?.role ?? null;

  return {
    loading,
    error,
    role,
    isMember: isSuperAdmin || Boolean(membership),
    canManage: isSuperAdmin || role === MEMBER_ROLES.OWNER || role === MEMBER_ROLES.MANAGER,
    isOwner: isSuperAdmin || role === MEMBER_ROLES.OWNER,
  };
}
