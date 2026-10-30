import apiClient from './apiClient';

const data = (request) => request.then((r) => r.data);

export const appointmentApi = {
  slots: (serviceId, date) =>
    data(apiClient.get(`/services/${serviceId}/appointment-slots`, { params: { date } })),
  book: (payload) => data(apiClient.post('/appointments', payload)),
  mine: (params) => data(apiClient.get('/appointments', { params })),
  get: (id) => data(apiClient.get(`/appointments/${id}`)),
  forBusiness: (businessId, params) =>
    data(apiClient.get(`/businesses/${businessId}/appointments`, { params })),
  cancel: (id, reason) => data(apiClient.post(`/appointments/${id}/cancel`, reason ? { reason } : undefined)),
  confirm: (id) => data(apiClient.post(`/appointments/${id}/confirm`)),
  checkIn: (id) => data(apiClient.post(`/appointments/${id}/check-in`)),
  complete: (id) => data(apiClient.post(`/appointments/${id}/complete`)),
  noShow: (id) => data(apiClient.post(`/appointments/${id}/no-show`)),
};
