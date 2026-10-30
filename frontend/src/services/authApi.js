import apiClient from './apiClient';

const REGISTER_PATHS = {
  CUSTOMER: '/auth/register/customer',
  BUSINESS_OWNER: '/auth/register/business-owner',
};

export const authApi = {
  register: (role, payload) => apiClient.post(REGISTER_PATHS[role], payload).then((r) => r.data),
  login: (email, password) => apiClient.post('/auth/login', { email, password }).then((r) => r.data),
  logout: (refreshToken) => apiClient.post('/auth/logout', { refresh_token: refreshToken }),
  me: () => apiClient.get('/auth/me').then((r) => r.data),
  forgotPassword: (email) => apiClient.post('/auth/forgot-password', { email }).then((r) => r.data),
  resetPassword: (token, newPassword) =>
    apiClient.post('/auth/reset-password', { token, new_password: newPassword }).then((r) => r.data),
};
