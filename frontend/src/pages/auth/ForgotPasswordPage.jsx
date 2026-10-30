import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Link, TextField, Typography } from '@mui/material';
import ErrorAlert from '../../components/ErrorAlert';
import SubmitButton from '../../components/forms/SubmitButton';
import { authApi } from '../../services/authApi';
import { getErrorMessage } from '../../utils/errors';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sentMessage, setSentMessage] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await authApi.forgotPassword(email.trim());
      setSentMessage(response.message);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Typography variant="h5" component="h1" gutterBottom>
        Reset your password
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Enter the email you registered with and we will send you a reset link.
      </Typography>

      <ErrorAlert message={error} />
      {sentMessage ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {sentMessage}
        </Alert>
      ) : (
        <>
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            margin="normal"
            required
            autoFocus
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <SubmitButton fullWidth size="large" loading={submitting} disabled={!email} sx={{ mt: 2 }}>
            Send reset link
          </SubmitButton>
        </>
      )}

      <Typography variant="body2" align="center" sx={{ mt: 3 }}>
        <Link component={RouterLink} to="/login">
          Back to sign in
        </Link>
      </Typography>
    </Box>
  );
}
