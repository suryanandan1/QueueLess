import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, List, ListItem, ListItemText, Typography } from '@mui/material';
import ErrorAlert from '../ErrorAlert';
import LoadingScreen from '../LoadingScreen';
import StatCard, { StatGrid } from '../StatCard';
import StatusChip from '../StatusChip';
import { useAsync } from '../../hooks/useAsync';
import { counterApi } from '../../services/counterApi';
import { serviceApi } from '../../services/serviceApi';

/** Today's statistics and counter overview for one service. */
export default function ServiceDetailsPanel({ service }) {
  const stats = useAsync(() => serviceApi.stats(service.id), [service.id]);
  const counters = useAsync(() => counterApi.forService(service.id), [service.id]);

  return (
    <Box>
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Today
      </Typography>
      <ErrorAlert message={stats.error} onRetry={stats.reload} />
      {stats.loading && !stats.data ? (
        <LoadingScreen message="Loading statistics…" />
      ) : (
        stats.data && (
          <StatGrid>
            <StatCard label="Tokens issued" value={stats.data.tokens_today} />
            <StatCard label="Waiting now" value={stats.data.tokens_waiting} />
            <StatCard label="Completed" value={stats.data.tokens_completed_today} />
            <StatCard
              label="Avg. service time"
              value={stats.data.average_service_minutes != null ? `${stats.data.average_service_minutes} min` : null}
              hint="Last 30 days"
            />
            <StatCard label="Upcoming appointments" value={stats.data.upcoming_appointments} />
          </StatGrid>
        )
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Counters
        </Typography>
        <Button size="small" component={RouterLink} to={`/businesses/${service.business_id}/counters`}>
          Manage counters
        </Button>
      </Box>
      <ErrorAlert message={counters.error} onRetry={counters.reload} />
      {counters.data?.length === 0 && (
        <Typography color="text.secondary" variant="body2">
          No counters yet. Counters are the desks where customers of this service are served.
        </Typography>
      )}
      <List dense disablePadding>
        {counters.data?.map((counter) => (
          <ListItem key={counter.id} divider secondaryAction={<StatusChip status={counter.status} />}>
            <ListItemText
              primary={counter.name}
              secondary={[
                counter.assigned_member_name ? `Staff: ${counter.assigned_member_name}` : 'Unassigned',
                counter.current_token ? `Now: ${counter.current_token.display_code}` : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
