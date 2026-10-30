import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Card, CardActions, CardContent, Chip, Typography } from '@mui/material';
import ErrorAlert from '../ErrorAlert';
import { useAsync } from '../../hooks/useAsync';
import { businessApi } from '../../services/businessApi';
import { ROLE_LABELS, categoryLabel } from '../../utils/constants';

function Metric({ label, value }) {
  return (
    <Box>
      <Typography variant="h6">{value ?? '—'}</Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

/** Card for a business the user belongs to, with live stats from the API. */
export default function BusinessSummaryCard({ business, role }) {
  const { data: stats, error, reload } = useAsync(() => businessApi.stats(business.id), [business.id]);

  return (
    <Card sx={{ display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
          <Chip size="small" label={categoryLabel(business.category)} />
          {role && <Chip size="small" variant="outlined" color="primary" label={ROLE_LABELS[role]} />}
          {!business.is_active && <Chip size="small" color="warning" label="Inactive" />}
        </Box>
        <Typography variant="h6" component="h2">
          {business.name}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {business.city || 'No city set'}
        </Typography>
        <ErrorAlert message={error} onRetry={reload} />
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1 }}>
          <Metric label="Active services" value={stats?.active_services} />
          <Metric label="Counters" value={stats?.active_counters} />
          <Metric label="Team" value={stats?.active_members} />
          <Metric label="Tokens today" value={stats?.tokens_today} />
        </Box>
      </CardContent>
      <CardActions sx={{ px: 2, pb: 2 }}>
        <Button component={RouterLink} to={`/businesses/${business.id}/overview`} variant="contained" size="small">
          Open
        </Button>
        <Button component={RouterLink} to={`/businesses/${business.id}/queues`} size="small">
          Queues
        </Button>
        <Button component={RouterLink} to={`/businesses/${business.id}/appointments`} size="small">
          Appointments
        </Button>
      </CardActions>
    </Card>
  );
}
