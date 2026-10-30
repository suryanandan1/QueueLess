import { useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  Typography,
} from '@mui/material';
import PersonAddAlt1OutlinedIcon from '@mui/icons-material/PersonAddAlt1Outlined';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ConfirmDialog from '../ConfirmDialog';
import EmptyState from '../EmptyState';
import ErrorAlert from '../ErrorAlert';
import LoadingScreen from '../LoadingScreen';
import PasswordField from '../forms/PasswordField';
import SubmitButton from '../forms/SubmitButton';
import { useAsync } from '../../hooks/useAsync';
import { useSnackbar } from '../../hooks/useSnackbar';
import { memberApi } from '../../services/businessApi';
import { MEMBER_ROLES, ROLE_LABELS } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';

const ASSIGNABLE_ROLES = [MEMBER_ROLES.MANAGER, MEMBER_ROLES.STAFF];
const emptyForm = { email: '', role: MEMBER_ROLES.STAFF, full_name: '', password: '' };

function AddMemberDialog({ open, businessId, onClose, onAdded }) {
  const [form, setForm] = useState(emptyForm);
  const [needsAccount, setNeedsAccount] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  const reset = () => {
    setForm(emptyForm);
    setNeedsAccount(false);
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    const payload = { email: form.email.trim(), role: form.role };
    if (needsAccount) Object.assign(payload, { full_name: form.full_name.trim(), password: form.password });
    try {
      const member = await memberApi.add(businessId, payload);
      reset();
      onAdded(member);
    } catch (err) {
      // 404 = no account for this email: offer to create a staff account instead.
      if (err.response?.status === 404 && !needsAccount) setNeedsAccount(true);
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (submitting) return;
        reset();
        onClose();
      }}
      maxWidth="sm"
      fullWidth
    >
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>Add team member</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Add someone who already has a QueueLess account, or create a staff account for them.
          </Typography>
          <ErrorAlert message={error} />
          <Stack spacing={2}>
            <TextField label="Email" name="email" type="email" required autoFocus value={form.email} onChange={handleChange} />
            <TextField select label="Role" name="role" value={form.role} onChange={handleChange}
              helperText="Managers can edit the business profile, services and counters.">
              {ASSIGNABLE_ROLES.map((role) => (
                <MenuItem key={role} value={role}>
                  {ROLE_LABELS[role]}
                </MenuItem>
              ))}
            </TextField>
            {needsAccount && (
              <>
                <TextField label="Full name" name="full_name" required value={form.full_name} onChange={handleChange} />
                <PasswordField
                  label="Temporary password"
                  name="password"
                  required
                  margin="none"
                  value={form.password}
                  onChange={handleChange}
                  helperText="Share it with them securely; they can change it under Account."
                />
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { reset(); onClose(); }} disabled={submitting}>
            Cancel
          </Button>
          <SubmitButton loading={submitting} disabled={!form.email}>
            {needsAccount ? 'Create account & add' : 'Add member'}
          </SubmitButton>
        </DialogActions>
      </form>
    </Dialog>
  );
}

export default function MembersPanel({ businessId, canEdit }) {
  const { notifySuccess, notifyError } = useSnackbar();
  const { data: members, loading, error, reload, setData } = useAsync(() => memberApi.list(businessId), [businessId]);
  const [addOpen, setAddOpen] = useState(false);
  const [removing, setRemoving] = useState(null);

  const replaceMember = (updated) => setData((list) => list.map((m) => (m.id === updated.id ? updated : m)));

  const updateMember = async (member, payload) => {
    try {
      replaceMember(await memberApi.update(businessId, member.id, payload));
      notifySuccess('Member updated.');
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  const confirmRemove = async () => {
    try {
      await memberApi.remove(businessId, removing.id);
      setData((list) => list.filter((m) => m.id !== removing.id));
      notifySuccess(`${removing.user.full_name} was removed.`);
      setRemoving(null);
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  if (loading && !members) return <LoadingScreen message="Loading team…" />;

  return (
    <Box>
      <ErrorAlert message={error} onRetry={reload} />
      {canEdit && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
          <Button variant="contained" startIcon={<PersonAddAlt1OutlinedIcon />} onClick={() => setAddOpen(true)}>
            Add member
          </Button>
        </Box>
      )}

      {members?.length === 0 ? (
        <EmptyState title="No team members yet" />
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Active</TableCell>
                {canEdit && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {members?.map((member) => {
                const isOwner = member.role === MEMBER_ROLES.OWNER;
                const editable = canEdit && !isOwner;
                return (
                  <TableRow key={member.id}>
                    <TableCell>{member.user.full_name}</TableCell>
                    <TableCell>{member.user.email}</TableCell>
                    <TableCell>
                      {editable ? (
                        <TextField
                          select
                          value={member.role}
                          onChange={(event) => updateMember(member, { role: event.target.value })}
                          sx={{ minWidth: 130 }}
                          slotProps={{ htmlInput: { 'aria-label': `Role of ${member.user.full_name}` } }}
                        >
                          {ASSIGNABLE_ROLES.map((role) => (
                            <MenuItem key={role} value={role}>
                              {ROLE_LABELS[role]}
                            </MenuItem>
                          ))}
                        </TextField>
                      ) : (
                        <Chip size="small" label={ROLE_LABELS[member.role]} color={isOwner ? 'primary' : 'default'} />
                      )}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={member.is_active}
                        disabled={!editable}
                        onChange={(event) => updateMember(member, { is_active: event.target.checked })}
                        slotProps={{ input: { 'aria-label': `Active status of ${member.user.full_name}` } }}
                      />
                    </TableCell>
                    {canEdit && (
                      <TableCell align="right">
                        {editable && (
                          <Tooltip title="Remove from business">
                            <IconButton aria-label={`Remove ${member.user.full_name}`} onClick={() => setRemoving(member)}>
                              <DeleteOutlineIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <AddMemberDialog
        open={addOpen}
        businessId={businessId}
        onClose={() => setAddOpen(false)}
        onAdded={(member) => {
          setData((list) => [...list, member]);
          setAddOpen(false);
          notifySuccess(`${member.user.full_name} was added.`);
        }}
      />
      <ConfirmDialog
        open={Boolean(removing)}
        title="Remove team member?"
        message={removing ? `${removing.user.full_name} will lose access to this business.` : ''}
        confirmLabel="Remove"
        confirmColor="error"
        onConfirm={confirmRemove}
        onClose={() => setRemoving(null)}
      />
    </Box>
  );
}
