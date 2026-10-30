import apiClient from './apiClient';

const data = (request) => request.then((r) => r.data);

export const notificationApi = {
  list: (params) => data(apiClient.get('/notifications', { params })),
  unreadCount: () => data(apiClient.get('/notifications/unread-count')),
  markRead: (id) => data(apiClient.patch(`/notifications/${id}/read`)),
  markAllRead: () => apiClient.post('/notifications/read-all'),
};
