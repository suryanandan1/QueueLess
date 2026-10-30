import { Button, CircularProgress } from '@mui/material';

export default function SubmitButton({ loading = false, children, disabled, ...props }) {
  return (
    <Button
      type="submit"
      variant="contained"
      disabled={loading || disabled}
      startIcon={loading ? <CircularProgress size={16} color="inherit" /> : undefined}
      {...props}
    >
      {children}
    </Button>
  );
}
