import axios from 'axios';
import { tokenStorage } from '../utils/tokenStorage';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// Endpoints where a 401 means "bad credentials", not "access token expired".
const NO_REFRESH_PATHS = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/register'];

let refreshPromise = null;
let sessionExpiredHandler = () => {};

export function onSessionExpired(handler) {
  sessionExpiredHandler = handler;
}

/**
 * Exchange the stored refresh token for a new pair. Concurrent callers share one
 * request: the backend rotates refresh tokens and treats reuse as theft, so two
 * parallel refreshes with the same token would end the session.
 */
export function refreshTokens() {
  if (!refreshPromise) {
    const refreshToken = tokenStorage.getRefreshToken();
    refreshPromise = (
      refreshToken
        ? axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
        : Promise.reject(new Error('No refresh token'))
    )
      .then(({ data }) => {
        tokenStorage.save(data);
        return data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isAuthPath = NO_REFRESH_PATHS.some((path) => original?.url?.startsWith(path));

    if (error.response?.status === 401 && original && !original._retried && !isAuthPath) {
      original._retried = true;
      try {
        const tokens = await refreshTokens();
        original.headers.Authorization = `Bearer ${tokens.access_token}`;
        return apiClient(original);
      } catch {
        tokenStorage.clear();
        sessionExpiredHandler();
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
