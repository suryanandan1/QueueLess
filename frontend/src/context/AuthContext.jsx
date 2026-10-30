import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { onSessionExpired } from '../services/apiClient';
import { authApi } from '../services/authApi';
import { tokenStorage } from '../utils/tokenStorage';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    onSessionExpired(() => setUser(null));

    if (!tokenStorage.getRefreshToken()) {
      setInitializing(false);
      return;
    }
    // The API client transparently refreshes an expired access token here.
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        tokenStorage.clear();
        setUser(null);
      })
      .finally(() => setInitializing(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const tokens = await authApi.login(email, password);
    tokenStorage.save(tokens);
    setUser(tokens.user);
    return tokens.user;
  }, []);

  const register = useCallback(
    async (role, payload) => {
      await authApi.register(role, payload);
      return login(payload.email, payload.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken();
    tokenStorage.clear();
    setUser(null);
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch (error) {
        // Local logout already happened; the server session will expire on its own.
        console.warn('Server-side logout failed', error);
      }
    }
  }, []);

  const value = useMemo(
    () => ({ user, setUser, initializing, isAuthenticated: Boolean(user), login, register, logout }),
    [user, initializing, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
