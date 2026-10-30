import { useState } from 'react';
import {
  Box,
  Button,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import AppointmentActions from '../../components/appointments/AppointmentActions';
import BusinessWorkspace from '../../components/business/BusinessWorkspace';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import StatusChip from '../../components/StatusChip';
import SelectField from '../../components/forms/SelectField';
import { useAsync } from '../../hooks/useAsync';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { appointmentApi } from '../../services/appointmentApi';
import { serviceApi } from '../../services/serviceApi';
import { addDays, formatTime, todayIn } from '../../utils/format';

const STATUS_OPTIONS = ['BOOKED', 'CONFIRMED', 'CHECKED_IN', 'COMPLETED', 'CANCELLED', 'NO_SHOW'].map((value) => ({
  value,
  label: value.replace('_', ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()),
}));

function Appointments({ business, access }) {
  const [day, setDay] = useState(() => todayIn(business.timezone));
  const [serviceId, setServiceId] = useState('');
  const [status, setStatus] = useState('');
  const services = useAsync(() => serviceApi.listForBusiness(business.id, true), [business.id]);
  const { data, loading, error, reload, setData } = useAsync(
    () =>
      appointmentApi.forBusiness(business.id, {
        date: day || undefined,
        service_id: serviceId || undefined,
        status: status || undefined,
        limit: 100,
      }),
    [business.id, day, serviceId, status],
  );
  useLiveRefresh(`/ws/businesses/${business.id}`, reload, { authenticated: true });

  const replace = (updated) =>
    setData((page) => ({ ...page, items: page.items.map((a) => (a.id === updated.id ? updated : a)) }));
  const bookable = (services.data ?? []).filter((service) => service.appointments_enabled);

  return (
    <>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'auto 1fr 1fr' }, gap: 2, mb: 2, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button size="small" onClick={() => setDay(addDays(day, -1))} aria-label="Previous day">‹</Button>
          <TextField type="date" label="Date" value={day} onChange={(e) => setDay(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }} sx={{ width: 170 }} />
          <Button size="small" onClick={() => setDay(addDays(day, 1))} aria-label="Next day">›</Button>
        </Box>
        <SelectField label="Service" value={serviceId} onChange={(e) => setServiceId(e.target.value)}
          options={(services.data ?? []).map((s) => ({ value: s.id, label: s.name }))} emptyLabel="All services" />
        <SelectField label="Status" value={status} onChange={(e) => setStatus(e.target.value)}
          options={STATUS_OPTIONS} emptyLabel="All statuses" />
      </Box>
      {services.data && bookable.length === 0 && (
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          No service takes appointments yet. Enable appointments in a service&apos;s settings under Services.
        </Typography>
      )}

      <ErrorAlert message={error} onRetry={reload} />
      <Card>
        {loading && !data ? (
          <LoadingScreen />
        ) : data?.items.length === 0 ? (
          <EmptyState title="No appointments for this selection" />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Service</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Notes</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data?.items.map((appointment) => (
                  <TableRow key={appointment.id}>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      {formatTime(appointment.scheduled_start, business.timezone)}–{formatTime(appointment.scheduled_end, business.timezone)}
                    </TableCell>
                    <TableCell>{appointment.service_name}</TableCell>
                    <TableCell>
                      {appointment.customer_name}
                      <Typography variant="caption" color="text.secondary" display="block">
                        {appointment.customer_phone ?? appointment.customer_email}
                      </Typography>
                    </TableCell>
                    <TableCell><StatusChip status={appointment.status} /></TableCell>
                    <TableCell sx={{ maxWidth: 200 }}>{appointment.notes ?? '—'}</TableCell>
                    <TableCell align="right">
                      <AppointmentActions appointment={appointment} canManage={access.canManage} onChanged={replace} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        Times are shown in {business.timezone}.
      </Typography>
    </>
  );
}

export default function AppointmentsManagePage() {
  return <BusinessWorkspace title="Appointments">{(context) => <Appointments {...context} />}</BusinessWorkspace>;
}
