import { useCallback, useEffect, useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Badge, IconButton, Tooltip } from '@mui/material';
import NotificationsNoneOutlinedIcon from '@mui/icons-material/NotificationsNoneOutlined';
import { notificationApi } from '../services/notificationApi';

const POLL_MS = 30000;

/** Header bell with the unread count; refreshes on navigation and every 30 s. */
export default function NotificationBell() {
  const { pathname } = useLocation();
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(() => {
    notificationApi
      .unreadCount()
      .then((result) => setUnread(result.unread))
      .catch((error) => console.warn('Could not load notification count', error));
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [refresh, pathname]);

  return (
    <Tooltip title="Notifications">
      <IconButton component={RouterLink} to="/notifications" aria-label={`Notifications, ${unread} unread`}>
        <Badge badgeContent={unread} color="error" max={99}>
          <NotificationsNoneOutlinedIcon />
        </Badge>
      </IconButton>
    </Tooltip>
  );
}
