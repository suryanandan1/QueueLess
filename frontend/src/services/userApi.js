import apiClient from './apiClient';

export const userApi = {
  updateProfile: (payload) => apiClient.patch('/users/me', payload).then((r) => r.data),
  changePassword: (currentPassword, newPassword) =>
    apiClient.post('/users/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};
