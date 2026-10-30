import { Alert, Button } from '@mui/material';

export default function ErrorAlert({ message, onRetry, sx }) {
  if (!message) return null;
  return (
    <Alert
      severity="error"
      sx={{ mb: 2, ...sx }}
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    >
      {message}
    </Alert>
  );
}
