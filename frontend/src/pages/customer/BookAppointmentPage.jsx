import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert, Box, Button, Card, CardContent, TextField, Typography } from '@mui/material';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import SubmitButton from '../../components/forms/SubmitButton';
import { useAsync } from '../../hooks/useAsync';
import { useSnackbar } from '../../hooks/useSnackbar';
import { appointmentApi } from '../../services/appointmentApi';
import { businessApi } from '../../services/businessApi';
import { serviceApi } from '../../services/serviceApi';
import { getErrorMessage } from '../../utils/errors';
import { addDays, formatTime, todayIn } from '../../utils/format';

function SlotPicker({ serviceId, day, timezone, selected, onSelect }) {
  const { data, loading, error, reload } = useAsync(() => appointmentApi.slots(serviceId, day), [serviceId, day]);
  if (loading && !data) return <LoadingScreen message="Loading available times…" />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  if (data.slots.length === 0) return <Typography color="text.secondary">No appointments on this day.</Typography>;
  const available = data.slots.filter((slot) => slot.is_available);
  return (
    <>
      {available.length === 0 && <Alert severity="info" sx={{ mb: 2 }}>This day is fully booked.</Alert>}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(96px, 1fr))', gap: 1 }}>
        {data.slots.map((slot) => (
          <Button
            key={slot.start}
            variant={selected === slot.start ? 'contained' : 'outlined'}
            disabled={!slot.is_available}
            onClick={() => onSelect(slot.start)}
          >
            {formatTime(slot.start, timezone)}
          </Button>
        ))}
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        {data.duration_minutes}-minute appointments · times in {timezone}
        {data.daily_remaining != null && ` · ${data.daily_remaining} left today`}
      </Typography>
    </>
  );
}

export default function BookAppointmentPage() {
  const { serviceId } = useParams();
  const navigate = useNavigate();
  const { notifySuccess } = useSnackbar();
  const [day, setDay] = useState(null);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { data, loading, error: loadError, reload } = useAsync(
    () => serviceApi.get(serviceId).then(async (service) => ({ service, business: await businessApi.get(service.business_id) })),
    [serviceId],
  );

  if (loading && !data) return <LoadingScreen />;
  if (loadError) return <ErrorAlert message={loadError} onRetry={reload} />;
  const { service, business } = data;
  const today = todayIn(business.timezone);
  const currentDay = day ?? today;

  const changeDay = (value) => {
    setDay(value);
    setSelected(null);
  };

  const book = async () => {
    setError('');
    setSubmitting(true);
    try {
      await appointmentApi.book({ service_id: service.id, scheduled_start: selected, notes: notes.trim() || null });
      notifySuccess('Appointment booked. You will be notified when it is confirmed.');
      navigate('/my/appointments');
    } catch (err) {
      setError(getErrorMessage(err));
      setSelected(null);
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 720 }}>
      <PageHeader title={`Book ${service.name}`} subtitle={business.name} />
      {!service.appointments_enabled ? (
        <Alert severity="info">This service does not take appointments.</Alert>
      ) : (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 2, flexWrap: 'wrap' }}>
              <Button size="small" disabled={currentDay <= today} onClick={() => changeDay(addDays(currentDay, -1))}>
                ‹ Previous
              </Button>
              <TextField type="date" label="Date" value={currentDay} sx={{ width: 180 }}
                onChange={(e) => e.target.value && changeDay(e.target.value)}
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: today } }} />
              <Button size="small" onClick={() => changeDay(addDays(currentDay, 1))}>Next ›</Button>
            </Box>
            <SlotPicker serviceId={service.id} day={currentDay} timezone={business.timezone}
              selected={selected} onSelect={setSelected} />
            <TextField label="Notes for the business (optional)" multiline minRows={2} value={notes}
              onChange={(e) => setNotes(e.target.value)} sx={{ mt: 3 }} slotProps={{ htmlInput: { maxLength: 1000 } }} />
            <ErrorAlert message={error} sx={{ mt: 2 }} />
            <SubmitButton type="button" loading={submitting} disabled={!selected} onClick={book} sx={{ mt: 2 }}>
              {selected ? `Book ${formatTime(selected, business.timezone)}` : 'Choose a time'}
            </SubmitButton>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
