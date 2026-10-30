import apiClient from './apiClient';

export const serviceApi = {
  listForBusiness: (businessId, includeInactive = false) =>
    apiClient
      .get(`/businesses/${businessId}/services`, { params: { include_inactive: includeInactive } })
      .then((r) => r.data),
  get: (serviceId) => apiClient.get(`/services/${serviceId}`).then((r) => r.data),
  create: (businessId, payload) =>
    apiClient.post(`/businesses/${businessId}/services`, payload).then((r) => r.data),
  update: (serviceId, payload) => apiClient.patch(`/services/${serviceId}`, payload).then((r) => r.data),
  remove: (serviceId) => apiClient.delete(`/services/${serviceId}`),
  stats: (serviceId) => apiClient.get(`/services/${serviceId}/stats`).then((r) => r.data),
};
