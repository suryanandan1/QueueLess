import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, Link, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { useAuth } from '../../hooks/useAuth';
import ErrorAlert from '../../components/ErrorAlert';
import PasswordField from '../../components/forms/PasswordField';
import SubmitButton from '../../components/forms/SubmitButton';
import { HOME_PATH_BY_ROLE, ROLES } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';

const PASSWORD_HINT = 'At least 8 characters, including a letter and a number.';

function validate(form) {
  const errors = {};
  if (form.full_name.trim().length < 2) errors.full_name = 'Enter your full name.';
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) errors.email = 'Enter a valid email address.';
  if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
    errors.password = PASSWORD_HINT;
  }
  if (form.password !== form.confirmPassword) errors.confirmPassword = 'Passwords do not match.';
  return errors;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState(ROLES.CUSTOMER);
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '', confirmPassword: '' });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = validate(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setError('');
    setSubmitting(true);
    try {
      const user = await register(role, {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        password: form.password,
      });
      navigate(HOME_PATH_BY_ROLE[user.role], { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Typography variant="h5" component="h1" gutterBottom>
        Create your account
      </Typography>

      <ToggleButtonGroup
        value={role}
        exclusive
        fullWidth
        color="primary"
        size="small"
        onChange={(_event, value) => value && setRole(value)}
        sx={{ my: 2 }}
      >
        <ToggleButton value={ROLES.CUSTOMER}>I&apos;m a customer</ToggleButton>
        <ToggleButton value={ROLES.BUSINESS_OWNER}>I run a business</ToggleButton>
      </ToggleButtonGroup>

      <ErrorAlert message={error} />

      <TextField
        label="Full name"
        name="full_name"
        autoComplete="name"
        margin="normal"
        required
        value={form.full_name}
        onChange={handleChange}
        error={Boolean(fieldErrors.full_name)}
        helperText={fieldErrors.full_name}
      />
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        margin="normal"
        required
        value={form.email}
        onChange={handleChange}
        error={Boolean(fieldErrors.email)}
        helperText={fieldErrors.email}
      />
      <TextField
        label="Phone (optional)"
        name="phone"
        autoComplete="tel"
        margin="normal"
        value={form.phone}
        onChange={handleChange}
      />
      <PasswordField
        name="password"
        autoComplete="new-password"
        required
        value={form.password}
        onChange={handleChange}
        error={Boolean(fieldErrors.password)}
        helperText={fieldErrors.password ?? PASSWORD_HINT}
      />
      <PasswordField
        label="Confirm password"
        name="confirmPassword"
        autoComplete="new-password"
        required
        value={form.confirmPassword}
        onChange={handleChange}
        error={Boolean(fieldErrors.confirmPassword)}
        helperText={fieldErrors.confirmPassword}
      />

      <SubmitButton fullWidth size="large" loading={submitting} sx={{ mt: 3 }}>
        {role === ROLES.BUSINESS_OWNER ? 'Create business account' : 'Create account'}
      </SubmitButton>

      <Typography variant="body2" align="center" sx={{ mt: 3 }}>
        Already have an account?{' '}
        <Link component={RouterLink} to="/login">
          Sign in
        </Link>
      </Typography>
    </Box>
  );
}
