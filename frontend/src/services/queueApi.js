import apiClient from './apiClient';

const data = (request) => request.then((r) => r.data);

export const queueApi = {
  listActive: (params) => data(apiClient.get('/queues', { params })),
  get: (queueId) => data(apiClient.get(`/queues/${queueId}`)),
  open: (serviceId, maxCapacity) =>
    data(apiClient.post('/queues', { service_id: serviceId, max_capacity: maxCapacity ?? null })),
  update: (queueId, payload) => data(apiClient.patch(`/queues/${queueId}`, payload)),
  pause: (queueId) => data(apiClient.post(`/queues/${queueId}/pause`)),
  resume: (queueId) => data(apiClient.post(`/queues/${queueId}/resume`)),
  close: (queueId) => data(apiClient.post(`/queues/${queueId}/close`)),
  join: (queueId) => data(apiClient.post(`/queues/${queueId}/join`)),
  addWalkIn: (queueId, payload) => data(apiClient.post(`/queues/${queueId}/walk-ins`, payload)),
  tokens: (queueId) => data(apiClient.get(`/queues/${queueId}/tokens`)),
  forBusiness: (businessId, params) => data(apiClient.get(`/businesses/${businessId}/queues`, { params })),
};

export const tokenApi = {
  mine: (params) => data(apiClient.get('/tokens', { params })),
  get: (tokenId) => data(apiClient.get(`/tokens/${tokenId}`)),
  cancel: (tokenId, reason) => data(apiClient.post(`/tokens/${tokenId}/cancel`, reason ? { reason } : undefined)),
  call: (tokenId, counterId) => data(apiClient.post(`/tokens/${tokenId}/call`, { counter_id: counterId })),
  recall: (tokenId, counterId) =>
    data(apiClient.post(`/tokens/${tokenId}/recall`, counterId ? { counter_id: counterId } : undefined)),
  start: (tokenId) => data(apiClient.post(`/tokens/${tokenId}/start`)),
  complete: (tokenId) => data(apiClient.post(`/tokens/${tokenId}/complete`)),
  skip: (tokenId) => data(apiClient.post(`/tokens/${tokenId}/skip`)),
  noShow: (tokenId) => data(apiClient.post(`/tokens/${tokenId}/no-show`)),
};
