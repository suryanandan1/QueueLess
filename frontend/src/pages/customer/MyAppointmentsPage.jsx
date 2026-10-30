import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Card, CardContent, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import ConfirmDialog from '../../components/ConfirmDialog';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import StatusChip from '../../components/StatusChip';
import { useAsync } from '../../hooks/useAsync';
import { useSnackbar } from '../../hooks/useSnackbar';
import { appointmentApi } from '../../services/appointmentApi';
import { getErrorMessage } from '../../utils/errors';
import { formatDateTime, formatTime } from '../../utils/format';

export function AppointmentCard({ appointment, onCancel }) {
  const tz = appointment.business_timezone;
  const cancellable =
    ['BOOKED', 'CONFIRMED'].includes(appointment.status) && new Date(appointment.scheduled_start) > new Date();
  return (
    <Card>
      <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <Box sx={{ flexGrow: 1, minWidth: 220 }}>
          <Typography fontWeight={600}>
            {appointment.service_name} · {appointment.business_name}
          </Typography>
          <Typography variant="body2">
            {formatDateTime(appointment.scheduled_start, tz)} – {formatTime(appointment.scheduled_end, tz)}{' '}
            <Typography component="span" variant="caption" color="text.secondary">({tz})</Typography>
          </Typography>
          {appointment.cancellation_reason && (
            <Typography variant="body2" color="text.secondary">Reason: {appointment.cancellation_reason}</Typography>
          )}
        </Box>
        <StatusChip status={appointment.status} />
        {onCancel && cancellable && (
          <Button color="error" size="small" onClick={() => onCancel(appointment)}>
            Cancel
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export default function MyAppointmentsPage() {
  const { notifySuccess, notifyError } = useSnackbar();
  const [filter, setFilter] = useState('upcoming');
  const [cancelling, setCancelling] = useState(null);
  const { data, loading, error, reload } = useAsync(
    () => appointmentApi.mine({ upcoming_only: filter === 'upcoming', limit: 50 }),
    [filter],
  );

  const confirmCancel = async () => {
    try {
      await appointmentApi.cancel(cancelling.id);
      notifySuccess('Appointment cancelled.');
      setCancelling(null);
      reload();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <>
      <PageHeader title="My appointments" />
      <ToggleButtonGroup value={filter} exclusive size="small" color="primary" sx={{ mb: 2 }}
        onChange={(_e, value) => value && setFilter(value)}>
        <ToggleButton value="upcoming">Upcoming</ToggleButton>
        <ToggleButton value="all">All bookings</ToggleButton>
      </ToggleButtonGroup>
      <ErrorAlert message={error} onRetry={reload} />
      {loading && !data ? (
        <LoadingScreen />
      ) : data?.items.length === 0 ? (
        <Card>
          <EmptyState
            title={filter === 'upcoming' ? 'No upcoming appointments' : 'No bookings yet'}
            description="Services that take appointments show a “Book appointment” button."
            action={<Button component={RouterLink} to="/customer" variant="contained">Find a business</Button>}
          />
        </Card>
      ) : (
        <Box sx={{ display: 'grid', gap: 1.5 }}>
          {data?.items.map((appointment) => (
            <AppointmentCard key={appointment.id} appointment={appointment} onCancel={setCancelling} />
          ))}
        </Box>
      )}
      <ConfirmDialog
        open={Boolean(cancelling)}
        title="Cancel this appointment?"
        message="The time slot will be released for other customers."
        confirmLabel="Cancel appointment"
        confirmColor="error"
        onConfirm={confirmCancel}
        onClose={() => setCancelling(null)}
      />
    </>
  );
}
