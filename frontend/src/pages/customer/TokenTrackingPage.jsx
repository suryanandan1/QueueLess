import { useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { Alert, Box, Button, Card, CardContent, Divider, Typography } from '@mui/material';
import ConfirmDialog from '../../components/ConfirmDialog';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import StatusChip from '../../components/StatusChip';
import WaitEstimate from '../../components/queue/WaitEstimate';
import { useAsync } from '../../hooks/useAsync';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { useSnackbar } from '../../hooks/useSnackbar';
import { queueApi, tokenApi } from '../../services/queueApi';
import { getErrorMessage } from '../../utils/errors';
import { formatDate, formatTime } from '../../utils/format';

const STATUS_MESSAGES = {
  WAITING: 'You are in the queue. Keep this page open; it updates automatically.',
  CALLED: 'It is your turn! Please go to the counter now.',
  SERVING: 'You are being served.',
  COMPLETED: 'Your visit is complete. Thank you!',
  SKIPPED: 'You were skipped because you were not at the counter. Please speak to the staff to be recalled.',
  CANCELLED: 'This token was cancelled.',
  NO_SHOW: 'This token was marked as a no-show.',
};

export default function TokenTrackingPage() {
  const { tokenId } = useParams();
  const { notifySuccess, notifyError } = useSnackbar();
  const [confirmCancel, setConfirmCancel] = useState(false);
  const { data, loading, error, reload } = useAsync(
    () =>
      tokenApi.get(tokenId).then(async (token) => ({
        token,
        queue: await queueApi.get(token.queue_session_id).catch(() => null),
      })),
    [tokenId],
  );
  useLiveRefresh(data ? `/ws/queues/${data.token.queue_session_id}` : null, reload, { pollMs: 15000 });

  if (loading && !data) return <LoadingScreen message="Loading your token…" />;
  if (error && !data) return <ErrorAlert message={error} onRetry={reload} />;
  const { token, queue } = data;
  const isActive = ['WAITING', 'CALLED', 'SERVING', 'SKIPPED'].includes(token.status);
  const canCancel = token.status === 'WAITING' || token.status === 'SKIPPED';

  const cancel = async () => {
    try {
      await tokenApi.cancel(token.id);
      notifySuccess('Your token was cancelled.');
      setConfirmCancel(false);
      reload();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto' }}>
      <Card>
        <CardContent sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="text.secondary">
            {token.business_name} · {token.service_name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {formatDate(token.session_date)}
          </Typography>
          <Typography variant="h1" fontWeight={800} color="primary" sx={{ my: 1, fontSize: { xs: '4rem', sm: '5.5rem' } }}>
            {token.display_code}
          </Typography>
          <StatusChip status={token.status} size="medium" />
          <Alert
            severity={token.status === 'CALLED' ? 'success' : token.status === 'SKIPPED' ? 'warning' : 'info'}
            sx={{ mt: 2, textAlign: 'left' }}
          >
            {STATUS_MESSAGES[token.status]}
            {token.status === 'CALLED' && token.counter_name && <strong> Counter: {token.counter_name}</strong>}
          </Alert>

          {token.status === 'WAITING' && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="overline" color="text.secondary">Your position</Typography>
              <Typography variant="h3" fontWeight={700}>{token.position}</Typography>
              <Box sx={{ mt: 1 }}>
                <WaitEstimate estimate={token.estimate} variant="h6" />
              </Box>
            </Box>
          )}
        </CardContent>
        {queue && isActive && (
          <>
            <Divider />
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">Now serving</Typography>
              <Typography>
                {queue.now_serving.length
                  ? queue.now_serving.map((t) => `${t.display_code}${t.counter_name ? ` at ${t.counter_name}` : ''}`).join(', ')
                  : 'Nobody is at a counter right now.'}
              </Typography>
              {queue.status !== 'OPEN' && (
                <Typography color="warning.main" variant="body2" sx={{ mt: 1 }}>
                  The queue is {queue.status.toLowerCase()}.
                </Typography>
              )}
            </CardContent>
          </>
        )}
        <Divider />
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            Joined {formatTime(token.joined_at)}
            {token.called_at && ` · called ${formatTime(token.called_at)}`}
            {token.completed_at && ` · completed ${formatTime(token.completed_at)}`}
            {token.cancelled_at && ` · cancelled ${formatTime(token.cancelled_at)}`}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
            <Button component={RouterLink} to="/my/tokens" variant="outlined">My tokens</Button>
            <Button component={RouterLink} to={`/explore/businesses/${token.business_id}`}>Business page</Button>
            {canCancel && (
              <Button color="error" onClick={() => setConfirmCancel(true)} sx={{ ml: 'auto' }}>
                Cancel token
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>
      <ConfirmDialog
        open={confirmCancel}
        title="Cancel your token?"
        message="You will lose your place in the queue. You can join again later if the queue is still open."
        confirmLabel="Cancel token"
        confirmColor="error"
        onConfirm={cancel}
        onClose={() => setConfirmCancel(false)}
      />
    </Box>
  );
}
