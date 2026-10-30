import apiClient from './apiClient';

export const businessApi = {
  list: (params) => apiClient.get('/businesses', { params }).then((r) => r.data),
  mine: () => apiClient.get('/businesses/mine').then((r) => r.data),
  get: (id) => apiClient.get(`/businesses/${id}`).then((r) => r.data),
  create: (payload) => apiClient.post('/businesses', payload).then((r) => r.data),
  update: (id, payload) => apiClient.patch(`/businesses/${id}`, payload).then((r) => r.data),
  updateWorkingHours: (id, workingHours) =>
    apiClient.put(`/businesses/${id}/working-hours`, { working_hours: workingHours }).then((r) => r.data),
  setStatus: (id, isActive) =>
    apiClient.patch(`/businesses/${id}/status`, { is_active: isActive }).then((r) => r.data),
  stats: (id) => apiClient.get(`/businesses/${id}/stats`).then((r) => r.data),
  analytics: (id, days) => apiClient.get(`/businesses/${id}/analytics`, { params: { days } }).then((r) => r.data),
};

export const memberApi = {
  list: (businessId) => apiClient.get(`/businesses/${businessId}/members`).then((r) => r.data),
  add: (businessId, payload) =>
    apiClient.post(`/businesses/${businessId}/members`, payload).then((r) => r.data),
  update: (businessId, memberId, payload) =>
    apiClient.patch(`/businesses/${businessId}/members/${memberId}`, payload).then((r) => r.data),
  remove: (businessId, memberId) =>
    apiClient.delete(`/businesses/${businessId}/members/${memberId}`),
};
