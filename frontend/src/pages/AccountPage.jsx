import { useState } from 'react';
import { Box, Card, CardContent, TextField, Typography } from '@mui/material';
import ErrorAlert from '../components/ErrorAlert';
import PageHeader from '../components/PageHeader';
import PasswordField from '../components/forms/PasswordField';
import SubmitButton from '../components/forms/SubmitButton';
import { useAuth } from '../hooks/useAuth';
import { useSnackbar } from '../hooks/useSnackbar';
import { userApi } from '../services/userApi';
import { ROLE_LABELS } from '../utils/constants';
import { getErrorMessage } from '../utils/errors';

function ProfileCard() {
  const { user, setUser } = useAuth();
  const { notifySuccess } = useSnackbar();
  const [form, setForm] = useState({ full_name: user.full_name, phone: user.phone ?? '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      setUser(await userApi.updateProfile({ full_name: form.full_name.trim(), phone: form.phone.trim() || null }));
      notifySuccess('Profile updated.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardContent component="form" onSubmit={handleSubmit} noValidate>
        <Typography variant="h6" gutterBottom>
          Profile
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {user.email} · {ROLE_LABELS[user.role]}
        </Typography>
        <ErrorAlert message={error} sx={{ mt: 2 }} />
        <TextField label="Full name" margin="normal" value={form.full_name}
          onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
        <TextField label="Phone" margin="normal" value={form.phone}
          onChange={(event) => setForm({ ...form, phone: event.target.value })} />
        <SubmitButton loading={saving} disabled={form.full_name.trim().length < 2} sx={{ mt: 2 }}>
          Save profile
        </SubmitButton>
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const { notifySuccess } = useSnackbar();
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const mismatch = form.confirm.length > 0 && form.next !== form.confirm;

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      await userApi.changePassword(form.current, form.next);
      setForm({ current: '', next: '', confirm: '' });
      notifySuccess('Password changed. Other devices have been signed out.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardContent component="form" onSubmit={handleSubmit} noValidate>
        <Typography variant="h6" gutterBottom>
          Change password
        </Typography>
        <ErrorAlert message={error} sx={{ mt: 2 }} />
        <PasswordField label="Current password" name="current" autoComplete="current-password" value={form.current} onChange={handleChange} />
        <PasswordField label="New password" name="next" autoComplete="new-password" value={form.next} onChange={handleChange}
          helperText="At least 8 characters, including a letter and a number." />
        <PasswordField label="Confirm new password" name="confirm" autoComplete="new-password" value={form.confirm} onChange={handleChange}
          error={mismatch} helperText={mismatch ? 'Passwords do not match.' : undefined} />
        <SubmitButton loading={saving} disabled={!form.current || !form.next || form.next !== form.confirm} sx={{ mt: 2 }}>
          Change password
        </SubmitButton>
      </CardContent>
    </Card>
  );
}

export default function AccountPage() {
  return (
    <>
      <PageHeader title="Account settings" />
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3, alignItems: 'start' }}>
        <ProfileCard />
        <PasswordCard />
      </Box>
    </>
  );
}
