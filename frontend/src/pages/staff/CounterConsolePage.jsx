import { useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from '@mui/material';
import CampaignOutlinedIcon from '@mui/icons-material/CampaignOutlined';
import AppointmentActions from '../../components/appointments/AppointmentActions';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import StatusChip from '../../components/StatusChip';
import { useAsync } from '../../hooks/useAsync';
import { useBusinessAccess } from '../../hooks/useBusinessAccess';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { useSnackbar } from '../../hooks/useSnackbar';
import { appointmentApi } from '../../services/appointmentApi';
import { businessApi } from '../../services/businessApi';
import { counterApi } from '../../services/counterApi';
import { tokenApi } from '../../services/queueApi';
import { getErrorMessage } from '../../utils/errors';
import { formatTime, minutesBetween, todayIn } from '../../utils/format';

function CurrentToken({ token, busy, run }) {
  if (!token) {
    return <EmptyState title="No customer at this counter" description="Call the next token when you are ready." />;
  }
  return (
    <Box sx={{ textAlign: 'center' }}>
      <Typography variant="h2" fontWeight={700} color="primary">
        {token.display_code}
      </Typography>
      <Box sx={{ my: 1 }}>
        <StatusChip status={token.status} size="medium" />
      </Box>
      <Typography variant="h6">{token.customer_name ?? 'Customer'}</Typography>
      {token.customer_phone && <Typography color="text.secondary">{token.customer_phone}</Typography>}
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        Joined {formatTime(token.joined_at)} · called {formatTime(token.called_at)}
        {token.recall_count > 0 && ` · recalled ${token.recall_count}×`}
        {token.service_started_at && ` · serving for ${minutesBetween(token.service_started_at, new Date())} min`}
      </Typography>
      <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
        {token.status === 'CALLED' && (
          <>
            <Button variant="contained" disabled={busy} onClick={() => run(() => tokenApi.start(token.id), 'Service started.')}>
              Start service
            </Button>
            <Button variant="outlined" disabled={busy} startIcon={<CampaignOutlinedIcon />}
              onClick={() => run(() => tokenApi.recall(token.id), `${token.display_code} called again.`)}>
              Recall
            </Button>
            <Button variant="outlined" color="warning" disabled={busy}
              onClick={() => run(() => tokenApi.skip(token.id), `${token.display_code} skipped.`)}>
              Skip
            </Button>
            <Button variant="outlined" color="error" disabled={busy}
              onClick={() => run(() => tokenApi.noShow(token.id), `${token.display_code} marked as no-show.`)}>
              No-show
            </Button>
          </>
        )}
        {token.status === 'SERVING' && (
          <Button variant="contained" color="success" size="large" disabled={busy}
            onClick={() => run(() => tokenApi.complete(token.id), `${token.display_code} completed.`)}>
            Complete service
          </Button>
        )}
      </Stack>
    </Box>
  );
}

function TodaysAppointments({ businessId, serviceId }) {
  const business = useAsync(() => businessApi.get(businessId), [businessId]);
  const timezone = business.data?.timezone;
  const { data, reload, setData } = useAsync(
    () => (timezone ? appointmentApi.forBusiness(businessId, { date: todayIn(timezone), service_id: serviceId, limit: 50 }) : null),
    [businessId, serviceId, timezone],
  );
  useLiveRefresh(`/ws/businesses/${businessId}`, reload, { authenticated: true, pollMs: 60000 });

  const items = (data?.items ?? []).filter((a) => !['CANCELLED'].includes(a.status));
  if (!timezone || items.length === 0) return null;
  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>Today&apos;s appointments</Typography>
        <List dense disablePadding>
          {items.map((appointment) => (
            <ListItem key={appointment.id} divider sx={{ flexWrap: 'wrap', gap: 1 }}>
              <ListItemText
                primary={`${formatTime(appointment.scheduled_start, timezone)} · ${appointment.customer_name}`}
                secondary={appointment.notes}
              />
              <StatusChip status={appointment.status} />
              <AppointmentActions
                appointment={appointment}
                canManage={false}
                onChanged={(updated) =>
                  setData((page) => ({ ...page, items: page.items.map((a) => (a.id === updated.id ? updated : a)) }))
                }
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
}

export default function CounterConsolePage() {
  const { counterId } = useParams();
  const { notifySuccess, notifyError } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const { data, loading, error, reload, setData } = useAsync(() => counterApi.console(counterId), [counterId]);
  const businessId = data?.counter.business_id;
  const access = useBusinessAccess(businessId);
  useLiveRefresh(data?.queue ? `/ws/queues/${data.queue.id}` : null, reload, { pollMs: 15000 });

  if (loading && !data) return <LoadingScreen message="Loading counter…" />;
  if (error && !data) return <ErrorAlert message={error} onRetry={reload} />;

  const { counter, queue, current_token: current, waiting, skipped, recently_completed: completed } = data;

  const run = async (action, message) => {
    setBusy(true);
    try {
      await action();
      notifySuccess(message);
      setData(await counterApi.console(counterId));
    } catch (err) {
      notifyError(getErrorMessage(err));
      reload();
    } finally {
      setBusy(false);
    }
  };

  const canCall = queue?.status === 'OPEN' && counter.is_active && !current;

  return (
    <>
      <PageHeader
        title={counter.name}
        subtitle={
          <Box component="span" sx={{ display: 'inline-flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            {counter.service_name} <StatusChip status={counter.status} />
            {queue && <StatusChip status={queue.status} />}
          </Box>
        }
        actions={
          access.canManage && (
            <Button component={RouterLink} to={`/businesses/${businessId}/queues`} variant="outlined">
              Manage queues
            </Button>
          )
        }
      />
      {!counter.is_active && <Alert severity="warning" sx={{ mb: 2 }}>This counter is offline. Ask a manager to bring it online.</Alert>}
      {!queue && <Alert severity="info" sx={{ mb: 2 }}>No queue has been opened today for {counter.service_name}.</Alert>}
      {queue?.status === 'PAUSED' && <Alert severity="warning" sx={{ mb: 2 }}>The queue is paused. Finish the current customer; calling resumes when the queue is resumed.</Alert>}
      {queue?.status === 'CLOSED' && <Alert severity="info" sx={{ mb: 2 }}>Today&apos;s queue is closed.</Alert>}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '3fr 2fr' }, gap: 3, alignItems: 'start' }}>
        <Box>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 1, flexWrap: 'wrap' }}>
                <Typography variant="h6">Current token</Typography>
                <Button variant="contained" size="large" disabled={busy || !canCall || waiting.length === 0}
                  onClick={() => run(() => counterApi.callNext(counter.id), 'Next customer called.')}>
                  Call next{waiting.length > 0 ? ` (${waiting[0].display_code})` : ''}
                </Button>
              </Box>
              <CurrentToken token={current} busy={busy} run={run} />
            </CardContent>
          </Card>
          <TodaysAppointments businessId={counter.business_id} serviceId={counter.service_id} />
        </Box>

        <Stack spacing={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Waiting ({waiting.length})</Typography>
              {waiting.length === 0 ? (
                <Typography color="text.secondary">Nobody is waiting.</Typography>
              ) : (
                <List dense disablePadding>
                  {waiting.map((token, index) => (
                    <ListItem key={token.id} divider
                      secondaryAction={
                        <Button size="small" disabled={busy || !canCall}
                          onClick={() => run(() => tokenApi.call(token.id, counter.id), `${token.display_code} called.`)}>
                          Call
                        </Button>
                      }>
                      <ListItemText
                        primary={`${index + 1}. ${token.display_code} · ${token.customer_name ?? 'Customer'}`}
                        secondary={`Joined ${formatTime(token.joined_at)}${token.is_walk_in ? ' · walk-in' : ''}`}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>

          {skipped.length > 0 && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Skipped ({skipped.length})</Typography>
                <List dense disablePadding>
                  {skipped.map((token) => (
                    <ListItem key={token.id} divider sx={{ flexWrap: 'wrap' }}>
                      <ListItemText primary={`${token.display_code} · ${token.customer_name ?? 'Customer'}`}
                        secondary={`Skipped ${formatTime(token.skipped_at)}`} />
                      <Button size="small" disabled={busy || !canCall}
                        onClick={() => run(() => tokenApi.recall(token.id, counter.id), `${token.display_code} recalled.`)}>
                        Recall
                      </Button>
                      <Button size="small" color="error" disabled={busy}
                        onClick={() => run(() => tokenApi.noShow(token.id), `${token.display_code} marked as no-show.`)}>
                        No-show
                      </Button>
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recently completed</Typography>
              {completed.length === 0 ? (
                <Typography color="text.secondary">No completed customers yet today.</Typography>
              ) : (
                <List dense disablePadding>
                  {completed.map((token) => (
                    <ListItem key={token.id} divider>
                      <ListItemText
                        primary={`${token.display_code} · ${token.customer_name ?? 'Customer'}`}
                        secondary={`${token.counter_name ?? ''} · done ${formatTime(token.completed_at)}${
                          token.service_started_at ? ` · ${minutesBetween(token.service_started_at, token.completed_at)} min` : ''
                        }`}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </>
  );
}
