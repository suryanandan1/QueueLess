import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  MenuItem,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import BusinessWorkspace from '../../components/business/BusinessWorkspace';
import ConfirmDialog from '../../components/ConfirmDialog';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import StatusChip from '../../components/StatusChip';
import SelectField from '../../components/forms/SelectField';
import SubmitButton from '../../components/forms/SubmitButton';
import { useAsync } from '../../hooks/useAsync';
import { useAuth } from '../../hooks/useAuth';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { useSnackbar } from '../../hooks/useSnackbar';
import { memberApi } from '../../services/businessApi';
import { counterApi } from '../../services/counterApi';
import { serviceApi } from '../../services/serviceApi';
import { getErrorMessage } from '../../utils/errors';

function AddCounterForm({ services, onAdded }) {
  const { notifySuccess } = useSnackbar();
  const [name, setName] = useState('');
  const [serviceId, setServiceId] = useState(services[0]?.id ?? '');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const counter = await counterApi.create(serviceId, { name: name.trim() });
      notifySuccess(`${counter.name} added.`);
      setName('');
      onAdded();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box component="form" onSubmit={submit} noValidate>
      <ErrorAlert message={error} />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <TextField label="Counter name" placeholder="e.g. Counter 3" value={name} onChange={(e) => setName(e.target.value)} />
        <SelectField label="Service" value={serviceId} onChange={(e) => setServiceId(e.target.value)}
          options={services.map((s) => ({ value: s.id, label: s.name }))} sx={{ minWidth: 200 }} />
        <SubmitButton loading={saving} disabled={!name.trim() || !serviceId} sx={{ flexShrink: 0 }}>
          Add counter
        </SubmitButton>
      </Stack>
    </Box>
  );
}

function Counters({ business, access }) {
  const { user } = useAuth();
  const { notifySuccess, notifyError } = useSnackbar();
  const [deleting, setDeleting] = useState(null);
  const { data, loading, error, reload } = useAsync(
    () =>
      Promise.all([
        counterApi.forBusiness(business.id),
        serviceApi.listForBusiness(business.id, true),
        memberApi.list(business.id),
      ]).then(([counters, services, members]) => ({ counters, services, members })),
    [business.id],
  );
  useLiveRefresh(`/ws/businesses/${business.id}`, reload, { authenticated: true });

  if (loading && !data) return <LoadingScreen />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  const { counters, services, members } = data;
  const canEdit = access.canManage;
  const activeMembers = members.filter((member) => member.is_active);
  const myMembershipId = members.find((member) => member.user.id === user.id)?.id;

  const update = async (counter, payload) => {
    try {
      await counterApi.update(counter.id, payload);
      notifySuccess('Counter updated.');
      reload();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  const confirmDelete = async () => {
    try {
      await counterApi.remove(deleting.id);
      notifySuccess('Counter deleted.');
      reload();
    } catch (err) {
      notifyError(getErrorMessage(err));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <>
      {canEdit && services.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <AddCounterForm services={services} onAdded={reload} />
          </CardContent>
        </Card>
      )}
      <Card>
        {counters.length === 0 ? (
          <EmptyState title="No counters yet" description={services.length ? 'Add a counter above.' : 'Create a service first.'} />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Counter</TableCell>
                  <TableCell>Service</TableCell>
                  <TableCell>Assigned staff</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Current token</TableCell>
                  <TableCell>Online</TableCell>
                  <TableCell align="right" />
                </TableRow>
              </TableHead>
              <TableBody>
                {counters.map((counter) => {
                  const canOperate = canEdit || counter.assigned_member_id === myMembershipId;
                  return (
                    <TableRow key={counter.id}>
                      <TableCell><strong>{counter.name}</strong></TableCell>
                      <TableCell>
                        {canEdit ? (
                          <TextField select value={counter.service_id} sx={{ minWidth: 150 }}
                            onChange={(e) => update(counter, { service_id: Number(e.target.value) })}
                            slotProps={{ htmlInput: { 'aria-label': `Service of ${counter.name}` } }}>
                            {services.map((service) => (
                              <MenuItem key={service.id} value={service.id}>{service.name}</MenuItem>
                            ))}
                          </TextField>
                        ) : (
                          counter.service_name
                        )}
                      </TableCell>
                      <TableCell>
                        {canEdit ? (
                          <TextField select value={counter.assigned_member_id ?? ''} sx={{ minWidth: 160 }}
                            onChange={(e) => update(counter, { assigned_member_id: e.target.value === '' ? null : Number(e.target.value) })}
                            slotProps={{ htmlInput: { 'aria-label': `Staff for ${counter.name}` } }}>
                            <MenuItem value=""><em>Unassigned</em></MenuItem>
                            {activeMembers.map((member) => (
                              <MenuItem key={member.id} value={member.id}>{member.user.full_name}</MenuItem>
                            ))}
                          </TextField>
                        ) : (
                          counter.assigned_member_name ?? 'Unassigned'
                        )}
                      </TableCell>
                      <TableCell><StatusChip status={counter.status} /></TableCell>
                      <TableCell>
                        {counter.current_token ? (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {counter.current_token.display_code} <StatusChip status={counter.current_token.status} />
                          </Box>
                        ) : '—'}
                      </TableCell>
                      <TableCell>
                        <Switch checked={counter.is_active} disabled={!canEdit}
                          onChange={(e) => update(counter, { is_active: e.target.checked })}
                          slotProps={{ input: { 'aria-label': `${counter.name} online` } }} />
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        {canOperate && (
                          <Button size="small" component={RouterLink} to={`/counters/${counter.id}/console`}>
                            Open console
                          </Button>
                        )}
                        {canEdit && (
                          <Tooltip title="Delete counter">
                            <IconButton aria-label={`Delete ${counter.name}`} onClick={() => setDeleting(counter)}>
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete counter?"
        message={deleting ? `${deleting.name} will be removed. Token history keeps working.` : ''}
        confirmLabel="Delete"
        confirmColor="error"
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}

export default function CountersPage() {
  return <BusinessWorkspace title="Counters">{(context) => <Counters {...context} />}</BusinessWorkspace>;
}
