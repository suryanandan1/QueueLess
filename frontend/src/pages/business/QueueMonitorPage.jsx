import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import BusinessWorkspace from '../../components/business/BusinessWorkspace';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import StatCard, { StatGrid } from '../../components/StatCard';
import StatusChip from '../../components/StatusChip';
import SubmitButton from '../../components/forms/SubmitButton';
import WaitEstimate from '../../components/queue/WaitEstimate';
import { useAsync } from '../../hooks/useAsync';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { useSnackbar } from '../../hooks/useSnackbar';
import { queueApi, tokenApi } from '../../services/queueApi';
import { getErrorMessage } from '../../utils/errors';
import { formatDate, formatTime } from '../../utils/format';

const FILTERS = {
  active: ['WAITING', 'CALLED', 'SERVING', 'SKIPPED'],
  finished: ['COMPLETED', 'CANCELLED', 'NO_SHOW'],
};

function WalkInForm({ queueId, onAdded }) {
  const { notifySuccess } = useSnackbar();
  const [form, setForm] = useState({ guest_name: '', guest_phone: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const token = await queueApi.addWalkIn(queueId, {
        guest_name: form.guest_name.trim(),
        guest_phone: form.guest_phone.trim() || null,
      });
      notifySuccess(`Issued ${token.display_code} to ${token.customer_name}.`);
      setForm({ guest_name: '', guest_phone: '' });
      onAdded();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box component="form" onSubmit={submit} noValidate>
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Walk-in customer
      </Typography>
      <ErrorAlert message={error} />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <TextField label="Name" value={form.guest_name} onChange={(e) => setForm({ ...form, guest_name: e.target.value })} />
        <TextField label="Phone (optional)" value={form.guest_phone} onChange={(e) => setForm({ ...form, guest_phone: e.target.value })} />
        <SubmitButton loading={saving} disabled={!form.guest_name.trim()} sx={{ flexShrink: 0 }}>
          Issue token
        </SubmitButton>
      </Stack>
    </Box>
  );
}

function Monitor({ queueId }) {
  const { notifySuccess, notifyError } = useSnackbar();
  const [filter, setFilter] = useState('active');
  const { data, loading, error, reload } = useAsync(
    () => Promise.all([queueApi.get(queueId), queueApi.tokens(queueId)]).then(([summary, tokens]) => ({ summary, tokens })),
    [queueId],
  );
  useLiveRefresh(`/ws/queues/${queueId}`, reload);

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  const { summary, tokens } = data;
  const visible = filter === 'all' ? tokens : tokens.filter((token) => FILTERS[filter].includes(token.status));

  const cancel = async (token) => {
    try {
      await tokenApi.cancel(token.id, 'Cancelled by staff');
      notifySuccess(`${token.display_code} cancelled.`);
      reload();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h6">{summary.service_name}</Typography>
        <StatusChip status={summary.status} />
        <Typography color="text.secondary">· {formatDate(summary.session_date)}</Typography>
      </Box>
      <StatGrid>
        <StatCard label="Waiting" value={summary.waiting_count} />
        <StatCard label="Issued" value={summary.tokens_issued} />
        <StatCard label="Capacity" value={summary.max_capacity ?? 'Unlimited'} hint={`${summary.active_count} active`} />
        <StatCard
          label="Now serving"
          value={summary.now_serving.map((t) => t.display_code).join(', ') || '—'}
        />
      </StatGrid>
      {summary.status !== 'CLOSED' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary">
              Wait for a customer joining now
            </Typography>
            <WaitEstimate estimate={summary.estimate_for_new_customer} />
            {summary.status === 'OPEN' && (
              <Box sx={{ mt: 2 }}>
                <WalkInForm queueId={queueId} onAdded={reload} />
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <Tabs value={filter} onChange={(_e, value) => setFilter(value)} sx={{ px: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Tab value="active" label="In queue" />
          <Tab value="finished" label="Finished" />
          <Tab value="all" label="All" />
        </Tabs>
        {visible.length === 0 ? (
          <EmptyState title="No tokens here" />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Token</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Counter</TableCell>
                  <TableCell>Joined</TableCell>
                  <TableCell>Called</TableCell>
                  <TableCell>Done</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.map((token) => (
                  <TableRow key={token.id}>
                    <TableCell><strong>{token.display_code}</strong></TableCell>
                    <TableCell>
                      {token.customer_name}
                      {token.is_walk_in && <Typography component="span" variant="caption" color="text.secondary"> (walk-in)</Typography>}
                    </TableCell>
                    <TableCell><StatusChip status={token.status} /></TableCell>
                    <TableCell>{token.counter_name ?? '—'}</TableCell>
                    <TableCell>{formatTime(token.joined_at)}</TableCell>
                    <TableCell>{formatTime(token.called_at)}</TableCell>
                    <TableCell>{formatTime(token.completed_at ?? token.cancelled_at ?? token.no_show_at)}</TableCell>
                    <TableCell align="right">
                      {['WAITING', 'SKIPPED'].includes(token.status) && (
                        <Button size="small" color="error" onClick={() => cancel(token)}>
                          Cancel
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
    </>
  );
}

export default function QueueMonitorPage() {
  const { queueId } = useParams();
  return <BusinessWorkspace title="Queue monitor">{() => <Monitor queueId={queueId} />}</BusinessWorkspace>;
}
