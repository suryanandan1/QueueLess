import { useState } from 'react';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Box, Link, Typography } from '@mui/material';
import ErrorAlert from '../../components/ErrorAlert';
import PasswordField from '../../components/forms/PasswordField';
import SubmitButton from '../../components/forms/SubmitButton';
import { useSnackbar } from '../../hooks/useSnackbar';
import { authApi } from '../../services/authApi';
import { getErrorMessage } from '../../utils/errors';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const { notifySuccess } = useSnackbar();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const mismatch = confirm.length > 0 && password !== confirm;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await authApi.resetPassword(token, password);
      notifySuccess(response.message);
      navigate('/login', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <Box>
        <Alert severity="warning" sx={{ mb: 2 }}>
          This reset link is incomplete. Request a new one.
        </Alert>
        <Link component={RouterLink} to="/forgot-password">
          Request a new reset link
        </Link>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Typography variant="h5" component="h1" gutterBottom>
        Choose a new password
      </Typography>
      <ErrorAlert message={error} />
      <PasswordField
        label="New password"
        autoComplete="new-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        helperText="At least 8 characters, including a letter and a number."
      />
      <PasswordField
        label="Confirm new password"
        autoComplete="new-password"
        required
        value={confirm}
        onChange={(event) => setConfirm(event.target.value)}
        error={mismatch}
        helperText={mismatch ? 'Passwords do not match.' : undefined}
      />
      <SubmitButton
        fullWidth
        size="large"
        loading={submitting}
        disabled={!password || password !== confirm}
        sx={{ mt: 2 }}
      >
        Reset password
      </SubmitButton>
    </Box>
  );
}
