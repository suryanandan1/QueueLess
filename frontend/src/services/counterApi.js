import apiClient from './apiClient';

const data = (request) => request.then((r) => r.data);

export const counterApi = {
  forBusiness: (businessId) => data(apiClient.get(`/businesses/${businessId}/counters`)),
  forService: (serviceId) => data(apiClient.get(`/services/${serviceId}/counters`)),
  assigned: () => data(apiClient.get('/counters/assigned')),
  get: (counterId) => data(apiClient.get(`/counters/${counterId}`)),
  console: (counterId) => data(apiClient.get(`/counters/${counterId}/console`)),
  callNext: (counterId) => data(apiClient.post(`/counters/${counterId}/call-next`)),
  create: (serviceId, payload) => data(apiClient.post(`/services/${serviceId}/counters`, payload)),
  update: (counterId, payload) => data(apiClient.patch(`/counters/${counterId}`, payload)),
  remove: (counterId) => apiClient.delete(`/counters/${counterId}`),
};
