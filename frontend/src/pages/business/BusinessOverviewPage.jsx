import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Card, CardContent, Typography } from '@mui/material';
import BusinessWorkspace from '../../components/business/BusinessWorkspace';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import StatCard, { StatGrid } from '../../components/StatCard';
import StatusChip from '../../components/StatusChip';
import WaitEstimate from '../../components/queue/WaitEstimate';
import { useAsync } from '../../hooks/useAsync';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { businessApi } from '../../services/businessApi';
import { counterApi } from '../../services/counterApi';
import { queueApi } from '../../services/queueApi';

function Overview({ business }) {
  const { data, error, reload } = useAsync(
    () =>
      Promise.all([
        businessApi.stats(business.id),
        queueApi.listActive({ business_id: business.id }),
        counterApi.forBusiness(business.id),
      ]).then(([stats, queues, counters]) => ({ stats, queues, counters })),
    [business.id],
  );
  useLiveRefresh(`/ws/businesses/${business.id}`, reload, { authenticated: true });

  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  if (!data) return null;
  const { stats, queues, counters } = data;

  return (
    <>
      <StatGrid>
        <StatCard label="Tokens today" value={stats.tokens_today} />
        <StatCard label="Waiting now" value={stats.tokens_waiting} />
        <StatCard label="Completed today" value={stats.tokens_completed_today} />
        <StatCard label="Upcoming appointments" value={stats.upcoming_appointments} />
        <StatCard label="Active services" value={stats.active_services} hint={`${stats.total_services} total`} />
        <StatCard label="Team members" value={stats.active_members} />
      </StatGrid>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '3fr 2fr' }, gap: 3, alignItems: 'start' }}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="h6">Live queues</Typography>
              <Button size="small" component={RouterLink} to={`/businesses/${business.id}/queues`}>
                Manage queues
              </Button>
            </Box>
            {queues.length === 0 ? (
              <EmptyState title="No queue is open today" description="Open a queue for a service to start accepting customers." />
            ) : (
              queues.map((queue) => (
                <Box key={queue.id} sx={{ py: 1.5, borderTop: 1, borderColor: 'divider' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Typography fontWeight={600} sx={{ flexGrow: 1 }}>
                      {queue.service_name}
                    </Typography>
                    <StatusChip status={queue.status} />
                    <Button size="small" component={RouterLink} to={`/businesses/${business.id}/queues/${queue.id}`}>
                      Monitor
                    </Button>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {queue.waiting_count} waiting · {queue.tokens_issued} issued today
                    {queue.now_serving.length > 0 &&
                      ` · Now: ${queue.now_serving.map((t) => `${t.display_code} (${t.counter_name})`).join(', ')}`}
                  </Typography>
                  <WaitEstimate estimate={queue.estimate_for_new_customer} />
                </Box>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="h6">Counters</Typography>
              <Button size="small" component={RouterLink} to={`/businesses/${business.id}/counters`}>
                Manage
              </Button>
            </Box>
            {counters.length === 0 ? (
              <EmptyState title="No counters yet" />
            ) : (
              counters.map((counter) => (
                <Box key={counter.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1, borderTop: 1, borderColor: 'divider' }}>
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Typography fontWeight={500}>{counter.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {counter.service_name} · {counter.assigned_member_name ?? 'Unassigned'}
                      {counter.current_token && ` · ${counter.current_token.display_code}`}
                    </Typography>
                  </Box>
                  <StatusChip status={counter.status} />
                </Box>
              ))
            )}
          </CardContent>
        </Card>
      </Box>
    </>
  );
}

export default function BusinessOverviewPage() {
  return <BusinessWorkspace title="Overview">{({ business }) => <Overview business={business} />}</BusinessWorkspace>;
}
