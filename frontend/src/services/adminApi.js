import apiClient from './apiClient';

export const adminApi = {
  stats: () => apiClient.get('/admin/stats').then((r) => r.data),
  listUsers: (params) => apiClient.get('/admin/users', { params }).then((r) => r.data),
  setUserStatus: (userId, isActive) =>
    apiClient.patch(`/admin/users/${userId}/status`, { is_active: isActive }).then((r) => r.data),
  listBusinesses: (params) => apiClient.get('/admin/businesses', { params }).then((r) => r.data),
  listAuditLogs: (params) => apiClient.get('/admin/audit-logs', { params }).then((r) => r.data),
};
