import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import BusinessWorkspace from '../../components/business/BusinessWorkspace';
import ConfirmDialog from '../../components/ConfirmDialog';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import StatusChip from '../../components/StatusChip';
import { useAsync } from '../../hooks/useAsync';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { useSnackbar } from '../../hooks/useSnackbar';
import { queueApi } from '../../services/queueApi';
import { serviceApi } from '../../services/serviceApi';
import { getErrorMessage } from '../../utils/errors';
import { formatDate, formatDateTime, todayIn } from '../../utils/format';

/** One row per active service with today's queue state and controls. */
function ServiceQueueRow({ service, queue, canManage, onChanged }) {
  const { notifySuccess, notifyError } = useSnackbar();
  const [capacity, setCapacity] = useState(queue?.max_capacity ?? service.max_queue_capacity ?? '');
  const [confirmClose, setConfirmClose] = useState(false);
  const [busy, setBusy] = useState(false);
  const capacityValue = capacity === '' ? null : Number(capacity);

  const run = async (action, message) => {
    setBusy(true);
    try {
      await action();
      notifySuccess(message);
      onChanged();
    } catch (err) {
      notifyError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const isLive = queue && queue.status !== 'CLOSED';
  return (
    <Box sx={{ py: 2, borderTop: 1, borderColor: 'divider' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
        <Box sx={{ flexGrow: 1, minWidth: 200 }}>
          <Typography fontWeight={600}>{service.name}</Typography>
          <Typography variant="body2" color="text.secondary">
            {queue
              ? `${queue.waiting_count} waiting · ${queue.tokens_issued} tokens today · capacity ${queue.max_capacity ?? 'unlimited'}`
              : 'No queue today'}
          </Typography>
        </Box>
        {queue ? <StatusChip status={queue.status} /> : <StatusChip status="CLOSED" label="Not opened" />}
        {queue && (
          <Button size="small" component={RouterLink} to={`/businesses/${service.business_id}/queues/${queue.id}`}>
            Monitor
          </Button>
        )}
      </Box>

      {canManage && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mt: 1.5 }}>
          <TextField
            label="Max in queue"
            type="number"
            value={capacity}
            onChange={(event) => setCapacity(event.target.value)}
            sx={{ width: 150 }}
            slotProps={{ htmlInput: { min: 1 } }}
            helperText="Empty = unlimited"
          />
          {!isLive && (
            <Button
              variant="contained"
              disabled={busy || !service.is_active}
              onClick={() => run(() => queueApi.open(service.id, capacityValue), `${service.name} queue opened.`)}
            >
              {queue ? 'Reopen queue' : 'Open queue'}
            </Button>
          )}
          {isLive && (
            <>
              <Button
                variant="outlined"
                disabled={busy}
                onClick={() =>
                  run(() => queueApi.update(queue.id, { max_capacity: capacityValue }), 'Capacity updated.')
                }
              >
                Save capacity
              </Button>
              {queue.status === 'OPEN' ? (
                <Button variant="outlined" color="warning" disabled={busy}
                  onClick={() => run(() => queueApi.pause(queue.id), 'Queue paused.')}>
                  Pause
                </Button>
              ) : (
                <Button variant="outlined" color="success" disabled={busy}
                  onClick={() => run(() => queueApi.resume(queue.id), 'Queue resumed.')}>
                  Resume
                </Button>
              )}
              <Button variant="outlined" color="error" disabled={busy} onClick={() => setConfirmClose(true)}>
                Close
              </Button>
            </>
          )}
        </Box>
      )}

      <ConfirmDialog
        open={confirmClose}
        title={`Close the ${service.name} queue?`}
        message="Customers who are still waiting will have their tokens cancelled and be notified. Tokens already at a counter can still be completed."
        confirmLabel="Close queue"
        confirmColor="error"
        onConfirm={async () => {
          await run(() => queueApi.close(queue.id), 'Queue closed.');
          setConfirmClose(false);
        }}
        onClose={() => setConfirmClose(false)}
      />
    </Box>
  );
}

function SessionHistory({ businessId, refreshKey }) {
  const [page, setPage] = useState(0);
  const pageSize = 10;
  const { data, error, reload } = useAsync(
    () => queueApi.forBusiness(businessId, { limit: pageSize, offset: page * pageSize }),
    [businessId, page, refreshKey],
  );
  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Queue history
        </Typography>
        <ErrorAlert message={error} onRetry={reload} />
        {data?.items.length === 0 ? (
          <EmptyState title="No queue sessions yet" />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Service</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Tokens</TableCell>
                  <TableCell>Opened</TableCell>
                  <TableCell>Closed</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {data?.items.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell>{formatDate(session.session_date)}</TableCell>
                    <TableCell>{session.service_name}</TableCell>
                    <TableCell><StatusChip status={session.status} /></TableCell>
                    <TableCell align="right">{session.tokens_issued}</TableCell>
                    <TableCell>{formatDateTime(session.opened_at)}</TableCell>
                    <TableCell>{formatDateTime(session.closed_at)}</TableCell>
                    <TableCell align="right">
                      <Button size="small" component={RouterLink} to={`/businesses/${businessId}/queues/${session.id}`}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        <TablePagination
          component="div"
          count={data?.total ?? 0}
          page={page}
          rowsPerPage={pageSize}
          rowsPerPageOptions={[pageSize]}
          onPageChange={(_event, value) => setPage(value)}
        />
      </CardContent>
    </Card>
  );
}

function Queues({ business, access }) {
  const { data, loading, error, reload } = useAsync(
    () =>
      Promise.all([
        serviceApi.listForBusiness(business.id),
        queueApi.listActive({ business_id: business.id }),
        queueApi.forBusiness(business.id, { limit: 50 }),
      ]).then(([services, active, recent]) => ({ services, active, recent: recent.items })),
    [business.id],
  );
  useLiveRefresh(`/ws/businesses/${business.id}`, reload, { authenticated: true });

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;

  // Today's session per service: an open/paused one, else one closed earlier today.
  const today = todayIn(business.timezone);
  const todaysQueue = (service) =>
    data.active.find((queue) => queue.service_id === service.id) ??
    data.recent.find((queue) => queue.service_id === service.id && queue.session_date === today);

  return (
    <>
      <Card>
        <CardContent>
          <Typography variant="h6">Today&apos;s queues</Typography>
          <Typography variant="body2" color="text.secondary">
            Pausing stops new customers joining and stops calling; closing ends the day&apos;s queue.
          </Typography>
          {data.services.length === 0 ? (
            <EmptyState title="No active services" description="Create a service before opening a queue." />
          ) : (
            data.services.map((service) => (
              <ServiceQueueRow
                key={`${service.id}-${todaysQueue(service)?.id ?? 'none'}`}
                service={service}
                queue={todaysQueue(service)}
                canManage={access.canManage}
                onChanged={reload}
              />
            ))
          )}
        </CardContent>
      </Card>
      <SessionHistory businessId={business.id} refreshKey={data} />
    </>
  );
}

export default function QueuesPage() {
  return <BusinessWorkspace title="Queues">{(context) => <Queues {...context} />}</BusinessWorkspace>;
}
