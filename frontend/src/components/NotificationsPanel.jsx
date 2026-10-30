import { Box, Button, Card, CardContent, CardHeader, List, ListItemButton, ListItemText, Typography } from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';
import EmptyState from './EmptyState';
import ErrorAlert from './ErrorAlert';
import LoadingScreen from './LoadingScreen';
import { useAsync } from '../hooks/useAsync';
import { useSnackbar } from '../hooks/useSnackbar';
import { notificationApi } from '../services/notificationApi';
import { getErrorMessage } from '../utils/errors';

const formatDate = (value) => new Date(value).toLocaleString();

export default function NotificationsPanel({ limit = 10, title = 'Notifications' }) {
  const { notifyError } = useSnackbar();
  const { data, loading, error, reload, setData } = useAsync(() => notificationApi.list({ limit }), [limit]);
  const items = data?.items ?? [];
  const hasUnread = items.some((item) => !item.is_read);

  const markRead = async (notification) => {
    if (notification.is_read) return;
    try {
      const updated = await notificationApi.markRead(notification.id);
      setData((page) => ({ ...page, items: page.items.map((n) => (n.id === updated.id ? updated : n)) }));
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  const markAllRead = async () => {
    try {
      await notificationApi.markAllRead();
      reload();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <Card>
      <CardHeader
        title={title}
        titleTypographyProps={{ variant: 'h6' }}
        action={
          hasUnread && (
            <Button size="small" onClick={markAllRead}>
              Mark all read
            </Button>
          )
        }
      />
      <CardContent sx={{ pt: 0 }}>
        <ErrorAlert message={error} onRetry={reload} />
        {loading && !data ? (
          <LoadingScreen message="Loading notifications…" />
        ) : items.length === 0 ? (
          <EmptyState title="You're all caught up" description="Updates about your queues and teams appear here." />
        ) : (
          <List disablePadding>
            {items.map((notification) => (
              <ListItemButton key={notification.id} onClick={() => markRead(notification)} sx={{ borderRadius: 2, alignItems: 'flex-start' }}>
                <Box sx={{ width: 18, pt: 0.75 }}>
                  {!notification.is_read && <CircleIcon color="primary" sx={{ fontSize: 10 }} aria-label="Unread" />}
                </Box>
                <ListItemText
                  primary={notification.title}
                  secondary={
                    <>
                      {notification.message}
                      <Typography component="span" variant="caption" display="block" color="text.disabled">
                        {formatDate(notification.created_at)}
                      </Typography>
                    </>
                  }
                  primaryTypographyProps={{ fontWeight: notification.is_read ? 400 : 600 }}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
}
