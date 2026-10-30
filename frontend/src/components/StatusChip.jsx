import { Chip } from '@mui/material';

const STYLES = {
  // tokens
  WAITING: { color: 'info', label: 'Waiting' },
  CALLED: { color: 'warning', label: 'Called' },
  SERVING: { color: 'primary', label: 'Serving' },
  COMPLETED: { color: 'success', label: 'Completed' },
  SKIPPED: { color: 'default', label: 'Skipped' },
  CANCELLED: { color: 'default', label: 'Cancelled' },
  NO_SHOW: { color: 'error', label: 'No-show' },
  // queues
  OPEN: { color: 'success', label: 'Open' },
  PAUSED: { color: 'warning', label: 'Paused' },
  CLOSED: { color: 'default', label: 'Closed' },
  // counters
  AVAILABLE: { color: 'success', label: 'Available' },
  BUSY: { color: 'warning', label: 'Busy' },
  OFFLINE: { color: 'default', label: 'Offline' },
  // appointments
  BOOKED: { color: 'info', label: 'Booked' },
  CONFIRMED: { color: 'primary', label: 'Confirmed' },
  CHECKED_IN: { color: 'warning', label: 'Checked in' },
};

export default function StatusChip({ status, size = 'small', ...props }) {
  const style = STYLES[status] ?? { color: 'default', label: status };
  return <Chip size={size} color={style.color} label={style.label} {...props} />;
}
