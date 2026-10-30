import { Box, Typography } from '@mui/material';

/** Shows a wait estimate, always labelled as an estimate, or the reason there is none. */
export default function WaitEstimate({ estimate, variant = 'body2' }) {
  if (!estimate) return null;
  if (estimate.minutes === null || estimate.minutes === undefined) {
    return (
      <Typography variant={variant} color="text.secondary">
        {estimate.note ?? 'No estimate available.'}
      </Typography>
    );
  }
  const basis =
    estimate.basis === 'history'
      ? `based on recent average of ${estimate.average_service_minutes} min per customer`
      : `based on the configured ${estimate.average_service_minutes} min per customer`;
  return (
    <Box>
      <Typography variant={variant}>
        {estimate.minutes === 0 ? 'Little or no wait' : `About ${estimate.minutes} min`}
        <Typography component="span" variant="caption" color="text.secondary">
          {' '}
          (estimate)
        </Typography>
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block">
        {estimate.people_ahead} ahead · {estimate.active_counters} counter{estimate.active_counters === 1 ? '' : 's'}{' '}
        open · {basis}. Not a guarantee.
      </Typography>
    </Box>
  );
}
