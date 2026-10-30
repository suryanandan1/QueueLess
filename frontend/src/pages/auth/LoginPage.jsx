import { useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { Box, Link, TextField, Typography } from '@mui/material';
import { useAuth } from '../../hooks/useAuth';
import ErrorAlert from '../../components/ErrorAlert';
import PasswordField from '../../components/forms/PasswordField';
import SubmitButton from '../../components/forms/SubmitButton';
import { HOME_PATH_BY_ROLE } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const user = await login(form.email.trim(), form.password);
      const fallback = HOME_PATH_BY_ROLE[user.role] ?? '/';
      navigate(location.state?.from?.pathname ?? fallback, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Typography variant="h5" component="h1" gutterBottom>
        Sign in
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Welcome back to QueueLess.
      </Typography>

      <ErrorAlert message={error} />

      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        margin="normal"
        required
        autoFocus
        value={form.email}
        onChange={handleChange}
      />
      <PasswordField
        name="password"
        autoComplete="current-password"
        required
        value={form.password}
        onChange={handleChange}
      />

      <Box sx={{ textAlign: 'right', mt: 0.5 }}>
        <Link component={RouterLink} to="/forgot-password" variant="body2">
          Forgot password?
        </Link>
      </Box>

      <SubmitButton
        fullWidth
        size="large"
        loading={submitting}
        disabled={!form.email || !form.password}
        sx={{ mt: 3 }}
      >
        Sign in
      </SubmitButton>

      <Typography variant="body2" align="center" sx={{ mt: 3 }}>
        New to QueueLess?{' '}
        <Link component={RouterLink} to="/register">
          Create an account
        </Link>
      </Typography>
    </Box>
  );
}
