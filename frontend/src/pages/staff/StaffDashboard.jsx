import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Card, CardActions, CardContent, Typography } from '@mui/material';
import BusinessSummaryCard from '../../components/business/BusinessSummaryCard';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import NotificationsPanel from '../../components/NotificationsPanel';
import PageHeader from '../../components/PageHeader';
import StatusChip from '../../components/StatusChip';
import { useAsync } from '../../hooks/useAsync';
import { useAuth } from '../../hooks/useAuth';
import { businessApi } from '../../services/businessApi';
import { counterApi } from '../../services/counterApi';

function MyCounters() {
  const { data: counters, error, reload } = useAsync(() => counterApi.assigned(), []);
  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  if (!counters) return null;
  if (counters.length === 0) {
    return (
      <Card sx={{ mb: 3 }}>
        <EmptyState
          title="No counter assigned to you"
          description="A manager can assign you to a counter under Counters. You can still view your workplaces below."
        />
      </Card>
    );
  }
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, mb: 3 }}>
      {counters.map((counter) => (
        <Card key={counter.id}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
              <Typography variant="h6">{counter.name}</Typography>
              <StatusChip status={counter.status} />
            </Box>
            <Typography color="text.secondary">{counter.service_name}</Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {counter.current_token
                ? `Now: ${counter.current_token.display_code} (${counter.current_token.status.toLowerCase()})`
                : 'No customer at the counter'}
            </Typography>
          </CardContent>
          <CardActions sx={{ px: 2, pb: 2 }}>
            <Button variant="contained" component={RouterLink} to={`/counters/${counter.id}/console`}>
              Open console
            </Button>
          </CardActions>
        </Card>
      ))}
    </Box>
  );
}

export default function StaffDashboard() {
  const { user } = useAuth();
  const { data: memberships, loading, error, reload } = useAsync(() => businessApi.mine(), []);

  return (
    <>
      <PageHeader title={`Welcome, ${user.full_name.split(' ')[0]}`} subtitle="Your counters and workplaces." />
      <ErrorAlert message={error} onRetry={reload} />
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3, alignItems: 'start' }}>
        <Box>
          <Typography variant="h6" gutterBottom>My counters</Typography>
          <MyCounters />
          <Typography variant="h6" gutterBottom>Workplaces</Typography>
          {loading && !memberships ? (
            <LoadingScreen message="Loading your workplaces…" />
          ) : memberships?.length === 0 ? (
            <Card>
              <EmptyState
                title="You are not part of any business yet"
                description="Ask a business owner to add you to their team using your account email."
              />
            </Card>
          ) : (
            <Box sx={{ display: 'grid', gap: 2 }}>
              {memberships?.map(({ business, role }) => (
                <BusinessSummaryCard key={business.id} business={business} role={role} />
              ))}
            </Box>
          )}
        </Box>
        <NotificationsPanel />
      </Box>
    </>
  );
}
