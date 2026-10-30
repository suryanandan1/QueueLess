import { useMemo, useState } from 'react';
import {
  Autocomplete,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material';
import ErrorAlert from '../ErrorAlert';
import SelectField from '../forms/SelectField';
import SubmitButton from '../forms/SubmitButton';
import { businessApi } from '../../services/businessApi';
import { BUSINESS_CATEGORIES } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';
import { defaultWeek, listTimezones, toApiHours } from '../../utils/hours';

const browserTimezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

const emptyForm = () => ({ name: '', category: 'OTHER', city: '', phone: '', timezone: browserTimezone() });

export default function CreateBusinessDialog({ open, onClose, onCreated }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const timezones = useMemo(listTimezones, []);

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  const handleClose = () => {
    if (submitting) return;
    setForm(emptyForm());
    setError('');
    onClose();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const business = await businessApi.create({
        name: form.name.trim(),
        category: form.category,
        city: form.city || null,
        phone: form.phone || null,
        timezone: form.timezone,
        working_hours: toApiHours(defaultWeek()),
      });
      setForm(emptyForm());
      onCreated(business);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>Create a business</DialogTitle>
        <DialogContent>
          <ErrorAlert message={error} />
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Business name" name="name" required autoFocus value={form.name} onChange={handleChange} />
            <SelectField label="Category" name="category" value={form.category} onChange={handleChange} options={BUSINESS_CATEGORIES} />
            <TextField label="City" name="city" value={form.city} onChange={handleChange} />
            <TextField label="Contact phone" name="phone" value={form.phone} onChange={handleChange} />
            <Autocomplete
              options={timezones}
              value={form.timezone}
              disableClearable
              onChange={(_event, value) => setForm({ ...form, timezone: value })}
              renderInput={(params) => (
                <TextField {...params} label="Timezone" helperText="Used for daily queues and opening hours." />
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={submitting}>
            Cancel
          </Button>
          <SubmitButton loading={submitting} disabled={form.name.trim().length < 2}>
            Create business
          </SubmitButton>
        </DialogActions>
      </form>
    </Dialog>
  );
}
