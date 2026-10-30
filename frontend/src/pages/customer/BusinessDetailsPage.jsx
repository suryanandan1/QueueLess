import { useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Typography,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ConfirmDialog from '../../components/ConfirmDialog';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import StatusChip from '../../components/StatusChip';
import WaitEstimate from '../../components/queue/WaitEstimate';
import { useAsync } from '../../hooks/useAsync';
import { useSnackbar } from '../../hooks/useSnackbar';
import { businessApi } from '../../services/businessApi';
import { queueApi } from '../../services/queueApi';
import { serviceApi } from '../../services/serviceApi';
import { DAY_NAMES, categoryLabel } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';
import { describeDay } from '../../utils/hours';

function HoursTable({ hours }) {
  if (!hours?.length) return <Typography color="text.secondary">Hours not published yet.</Typography>;
  return (
    <Table size="small">
      <TableBody>
        {DAY_NAMES.map((name, day) => (
          <TableRow key={name}>
            <TableCell sx={{ pl: 0 }}>{name}</TableCell>
            <TableCell align="right" sx={{ pr: 0 }}>
              {describeDay(hours.find((entry) => entry.day_of_week === day))}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ServiceRow({ service, queue, onJoin }) {
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <Typography fontWeight={600}>{service.name}</Typography>
        {queue ? <StatusChip status={queue.status} label={queue.status === 'OPEN' ? 'Queue open' : undefined} />
          : <Chip size="small" label="No queue today" />}
      </Box>
      {service.description && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {service.description}
        </Typography>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <AccessTimeIcon fontSize="inherit" /> About {service.estimated_duration_minutes} min per customer
      </Typography>
      {queue && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="body2">
            {queue.waiting_count} waiting
            {queue.now_serving.length > 0 && ` · now serving ${queue.now_serving.map((t) => t.display_code).join(', ')}`}
          </Typography>
          <WaitEstimate estimate={queue.estimate_for_new_customer} />
          {!queue.accepting_customers && (
            <Typography variant="body2" color="warning.main">{queue.not_accepting_reason}</Typography>
          )}
        </Box>
      )}
      <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
        {queue && (
          <Button variant="contained" size="small" disabled={!queue.accepting_customers} onClick={() => onJoin(service, queue)}>
            Join queue
          </Button>
        )}
        {service.appointments_enabled && (
          <Button variant="outlined" size="small" component={RouterLink} to={`/book/${service.id}`}>
            Book appointment
          </Button>
        )}
      </Stack>
    </Box>
  );
}

export default function BusinessDetailsPage() {
  const { businessId } = useParams();
  const navigate = useNavigate();
  const { notifyError } = useSnackbar();
  const [joining, setJoining] = useState(null);
  const { data, loading, error, reload } = useAsync(
    () =>
      Promise.all([
        businessApi.get(businessId),
        serviceApi.listForBusiness(businessId),
        queueApi.listActive({ business_id: businessId }),
      ]),
    [businessId],
  );

  if (loading && !data) return <LoadingScreen message="Loading business…" />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;

  const [business, services, queues] = data;
  const address = [business.address_line, business.city, business.state, business.postal_code, business.country]
    .filter(Boolean)
    .join(', ');

  const confirmJoin = async () => {
    try {
      const token = await queueApi.join(joining.queue.id);
      navigate(`/my/tokens/${token.id}`);
    } catch (err) {
      notifyError(getErrorMessage(err));
      setJoining(null);
      reload();
    }
  };

  return (
    <>
      <PageHeader title={business.name} subtitle={categoryLabel(business.category)} />
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 3, alignItems: 'start' }}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Services
            </Typography>
            {services.length === 0 ? (
              <EmptyState title="No services listed yet" />
            ) : (
              <Stack divider={<Divider flexItem />} spacing={2}>
                {services.map((service) => (
                  <ServiceRow
                    key={service.id}
                    service={service}
                    queue={queues.find((queue) => queue.service_id === service.id)}
                    onJoin={(svc, queue) => setJoining({ service: svc, queue })}
                  />
                ))}
              </Stack>
            )}
          </CardContent>
        </Card>

        <Stack spacing={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                About
              </Typography>
              {business.description && <Typography sx={{ mb: 2 }}>{business.description}</Typography>}
              {address && <Typography variant="body2">{address}</Typography>}
              {business.phone && <Typography variant="body2">Phone: {business.phone}</Typography>}
              {business.email && <Typography variant="body2">Email: {business.email}</Typography>}
              {!business.description && !address && !business.phone && !business.email && (
                <Typography color="text.secondary">No contact details published.</Typography>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Working hours
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Times in {business.timezone}
              </Typography>
              <HoursTable hours={business.working_hours} />
            </CardContent>
          </Card>
        </Stack>
      </Box>

      <ConfirmDialog
        open={Boolean(joining)}
        title={joining ? `Join the ${joining.service.name} queue?` : ''}
        message={
          joining
            ? `You will get a digital token and can track your place in line. ${joining.queue.waiting_count} people are waiting now.`
            : ''
        }
        confirmLabel="Get my token"
        onConfirm={confirmJoin}
        onClose={() => setJoining(null)}
      />
    </>
  );
}
