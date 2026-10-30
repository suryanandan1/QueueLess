import { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import ErrorAlert from '../ErrorAlert';
import SubmitButton from '../forms/SubmitButton';
import WorkingHoursEditor from '../forms/WorkingHoursEditor';
import { getErrorMessage } from '../../utils/errors';
import { toApiHours, toEditorHours, validateHours } from '../../utils/hours';

function formFromService(service) {
  return {
    name: service?.name ?? '',
    description: service?.description ?? '',
    estimated_duration_minutes: service?.estimated_duration_minutes ?? 15,
    max_queue_capacity: service?.max_queue_capacity ?? '',
    is_active: service?.is_active ?? true,
    is_available: service?.is_available ?? true,
    customHours: Boolean(service?.operating_hours),
    operating_hours: toEditorHours(service?.operating_hours),
    token_prefix: service?.token_prefix ?? 'A',
    appointments_enabled: service?.appointments_enabled ?? false,
    appointment_duration_minutes: service?.appointment_duration_minutes ?? '',
    appointment_slot_capacity: service?.appointment_slot_capacity ?? 1,
    appointment_daily_capacity: service?.appointment_daily_capacity ?? '',
    customBookingHours: Boolean(service?.appointment_hours),
    appointment_hours: toEditorHours(service?.appointment_hours),
  };
}

const optionalInt = (value) => (value === '' || value === null ? null : Number(value));
const isPositiveInt = (value) => Number.isInteger(value) && value > 0;

/** Create (service = null) or edit a service. `onSubmit(payload)` must return a promise. */
export default function ServiceFormDialog({ open, service, onClose, onSubmit }) {
  const [form, setForm] = useState(() => formFromService(service));
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(formFromService(service));
      setError('');
    }
  }, [open, service]);

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const handleToggle = (event) => setForm({ ...form, [event.target.name]: event.target.checked });

  const handleSubmit = async (event) => {
    event.preventDefault();
    const duration = Number(form.estimated_duration_minutes);
    if (!Number.isInteger(duration) || duration < 1 || duration > 480) {
      setError('Estimated duration must be a whole number between 1 and 480 minutes.');
      return;
    }
    const capacity = form.max_queue_capacity === '' ? null : Number(form.max_queue_capacity);
    if (capacity !== null && (!Number.isInteger(capacity) || capacity < 1)) {
      setError('Maximum queue capacity must be a positive whole number, or empty for no limit.');
      return;
    }
    if (!/^[A-Za-z]{1,3}$/.test(form.token_prefix.trim())) {
      setError('Token prefix must be 1-3 letters, e.g. A.');
      return;
    }
    const slotDuration = optionalInt(form.appointment_duration_minutes);
    const slotCapacity = Number(form.appointment_slot_capacity);
    const dailyCapacity = optionalInt(form.appointment_daily_capacity);
    if (form.appointments_enabled) {
      if (slotDuration !== null && (!isPositiveInt(slotDuration) || slotDuration < 5)) {
        setError('Appointment length must be at least 5 minutes, or empty to use the service duration.');
        return;
      }
      if (!isPositiveInt(slotCapacity) || (dailyCapacity !== null && !isPositiveInt(dailyCapacity))) {
        setError('Booking capacities must be positive whole numbers.');
        return;
      }
    }
    for (const [enabled, hours] of [
      [form.customHours, form.operating_hours],
      [form.appointments_enabled && form.customBookingHours, form.appointment_hours],
    ]) {
      const hoursError = enabled ? validateHours(hours) : null;
      if (hoursError) {
        setError(hoursError);
        return;
      }
    }

    setError('');
    setSubmitting(true);
    try {
      await onSubmit({
        name: form.name.trim(),
        description: form.description.trim() || null,
        estimated_duration_minutes: duration,
        max_queue_capacity: capacity,
        is_active: form.is_active,
        is_available: form.is_available,
        operating_hours: form.customHours ? toApiHours(form.operating_hours) : null,
        token_prefix: form.token_prefix.trim().toUpperCase(),
        appointments_enabled: form.appointments_enabled,
        appointment_duration_minutes: slotDuration,
        appointment_slot_capacity: slotCapacity,
        appointment_daily_capacity: dailyCapacity,
        appointment_hours:
          form.appointments_enabled && form.customBookingHours ? toApiHours(form.appointment_hours) : null,
      });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={submitting ? undefined : onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>{service ? `Edit ${service.name}` : 'New service'}</DialogTitle>
        <DialogContent>
          <ErrorAlert message={error} />
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Service name" name="name" required autoFocus value={form.name} onChange={handleChange}
              placeholder="e.g. Cash Deposit, Haircut" />
            <TextField label="Description" name="description" multiline minRows={2} value={form.description} onChange={handleChange} />
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
              <TextField
                label="Estimated duration (minutes)"
                name="estimated_duration_minutes"
                type="number"
                required
                value={form.estimated_duration_minutes}
                onChange={handleChange}
                slotProps={{ htmlInput: { min: 1, max: 480 } }}
                helperText="Average time to serve one customer."
              />
              <TextField
                label="Maximum queue capacity"
                name="max_queue_capacity"
                type="number"
                value={form.max_queue_capacity}
                onChange={handleChange}
                slotProps={{ htmlInput: { min: 1 } }}
                helperText="Default for new queues. Leave empty for no limit."
              />
              <TextField
                label="Token prefix"
                name="token_prefix"
                value={form.token_prefix}
                onChange={handleChange}
                slotProps={{ htmlInput: { maxLength: 3 } }}
                helperText={`Tokens look like ${(form.token_prefix || 'A').toUpperCase()}001.`}
              />
            </Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
              <FormControlLabel
                control={<Switch name="is_active" checked={form.is_active} onChange={handleToggle} />}
                label="Active (listed for customers)"
              />
              <FormControlLabel
                control={<Switch name="is_available" checked={form.is_available} onChange={handleToggle} />}
                label="Available (accepting customers)"
              />
            </Box>
            <Box>
              <FormControlLabel
                control={<Switch name="customHours" checked={form.customHours} onChange={handleToggle} />}
                label="Use custom operating hours"
              />
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {form.customHours
                  ? 'This service runs on its own schedule.'
                  : 'This service follows the business working hours.'}
              </Typography>
              {form.customHours && (
                <WorkingHoursEditor
                  value={form.operating_hours}
                  onChange={(operating_hours) => setForm({ ...form, operating_hours })}
                />
              )}
            </Box>
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                Appointments
              </Typography>
              <FormControlLabel
                control={<Switch name="appointments_enabled" checked={form.appointments_enabled} onChange={handleToggle} />}
                label="Customers can book appointments in advance"
              />
              {form.appointments_enabled && (
                <>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr' }, gap: 2, mt: 1 }}>
                    <TextField
                      label="Appointment length (min)"
                      name="appointment_duration_minutes"
                      type="number"
                      value={form.appointment_duration_minutes}
                      onChange={handleChange}
                      helperText="Empty = service duration."
                    />
                    <TextField
                      label="Bookings per slot"
                      name="appointment_slot_capacity"
                      type="number"
                      value={form.appointment_slot_capacity}
                      onChange={handleChange}
                      slotProps={{ htmlInput: { min: 1 } }}
                    />
                    <TextField
                      label="Bookings per day"
                      name="appointment_daily_capacity"
                      type="number"
                      value={form.appointment_daily_capacity}
                      onChange={handleChange}
                      helperText="Empty = no daily limit."
                    />
                  </Box>
                  <FormControlLabel
                    sx={{ mt: 1 }}
                    control={<Switch name="customBookingHours" checked={form.customBookingHours} onChange={handleToggle} />}
                    label="Use separate booking hours"
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {form.customBookingHours
                      ? 'Appointments can only be booked within these hours.'
                      : 'Bookable hours follow the service (or business) hours.'}
                  </Typography>
                  {form.customBookingHours && (
                    <WorkingHoursEditor
                      value={form.appointment_hours}
                      onChange={(appointment_hours) => setForm({ ...form, appointment_hours })}
                    />
                  )}
                </>
              )}
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <SubmitButton loading={submitting} disabled={form.name.trim().length < 2}>
            {service ? 'Save changes' : 'Create service'}
          </SubmitButton>
        </DialogActions>
      </form>
    </Dialog>
  );
}
