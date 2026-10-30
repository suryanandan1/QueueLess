import { useEffect, useRef } from 'react';
import { API_BASE_URL } from '../services/apiClient';
import { tokenStorage } from '../utils/tokenStorage';

const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');
const RECONNECT_DELAY_MS = 3000;

/**
 * Call `refresh` whenever the server announces a change on a WebSocket channel,
 * plus a slower polling fallback in case the socket is unavailable.
 *
 * `channel` is e.g. `/ws/queues/12` or `/ws/businesses/3` (null disables).
 * Business channels require authentication, so the access token is appended.
 */
export function useLiveRefresh(channel, refresh, { pollMs = 20000, authenticated = false } = {}) {
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    if (!channel) return undefined;
    let socket;
    let reconnectTimer;
    let stopped = false;

    const connect = () => {
      const query = authenticated ? `?token=${encodeURIComponent(tokenStorage.getAccessToken() ?? '')}` : '';
      socket = new WebSocket(`${WS_BASE_URL}${channel}${query}`);
      socket.onmessage = () => refreshRef.current();
      socket.onclose = () => {
        if (!stopped) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    };

    try {
      connect();
    } catch (error) {
      console.warn('Live updates unavailable; falling back to polling', error);
    }
    const poller = setInterval(() => refreshRef.current(), pollMs);

    return () => {
      stopped = true;
      clearInterval(poller);
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [channel, pollMs, authenticated]);
}
