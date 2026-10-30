import { useState } from 'react';
import { Box, Button } from '@mui/material';
import ConfirmDialog from '../ConfirmDialog';
import { useSnackbar } from '../../hooks/useSnackbar';
import { appointmentApi } from '../../services/appointmentApi';
import { getErrorMessage } from '../../utils/errors';

/**
 * Business-side actions for one appointment. Only actions valid for the current
 * status are shown; the backend validates every transition again.
 */
export default function AppointmentActions({ appointment, canManage, onChanged }) {
  const { notifySuccess, notifyError } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const { status } = appointment;
  const started = new Date(appointment.scheduled_start) <= new Date();

  const run = async (action, message) => {
    setBusy(true);
    try {
      onChanged(await action(appointment.id));
      notifySuccess(message);
    } catch (err) {
      notifyError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const pending = status === 'BOOKED' || status === 'CONFIRMED';
  return (
    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
      {canManage && status === 'BOOKED' && (
        <Button size="small" disabled={busy} onClick={() => run(appointmentApi.confirm, 'Appointment confirmed.')}>
          Confirm
        </Button>
      )}
      {pending && (
        <Button size="small" disabled={busy} onClick={() => run(appointmentApi.checkIn, 'Customer checked in.')}>
          Check in
        </Button>
      )}
      {status === 'CHECKED_IN' && (
        <Button size="small" variant="contained" disabled={busy} onClick={() => run(appointmentApi.complete, 'Appointment completed.')}>
          Complete
        </Button>
      )}
      {pending && started && (
        <Button size="small" color="warning" disabled={busy} onClick={() => run(appointmentApi.noShow, 'Marked as no-show.')}>
          No-show
        </Button>
      )}
      {canManage && pending && (
        <Button size="small" color="error" disabled={busy} onClick={() => setConfirmCancel(true)}>
          Cancel
        </Button>
      )}
      <ConfirmDialog
        open={confirmCancel}
        title="Cancel this booking?"
        message={`${appointment.customer_name} will be notified that the business cancelled the appointment.`}
        confirmLabel="Cancel booking"
        confirmColor="error"
        onConfirm={async () => {
          await run((id) => appointmentApi.cancel(id, 'Cancelled by the business'), 'Booking cancelled.');
          setConfirmCancel(false);
        }}
        onClose={() => setConfirmCancel(false)}
      />
    </Box>
  );
}
