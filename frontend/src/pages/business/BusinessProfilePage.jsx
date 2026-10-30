import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import ConfirmDialog from '../../components/ConfirmDialog';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import BusinessNav from '../../components/business/BusinessNav';
import MembersPanel from '../../components/business/MembersPanel';
import SelectField from '../../components/forms/SelectField';
import SubmitButton from '../../components/forms/SubmitButton';
import WorkingHoursEditor from '../../components/forms/WorkingHoursEditor';
import { useAsync } from '../../hooks/useAsync';
import { useBusinessAccess } from '../../hooks/useBusinessAccess';
import { useSnackbar } from '../../hooks/useSnackbar';
import { businessApi } from '../../services/businessApi';
import { BUSINESS_CATEGORIES, ROLE_LABELS } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';
import { listTimezones, toApiHours, toEditorHours, validateHours } from '../../utils/hours';

const PROFILE_FIELDS = [
  'name', 'category', 'description', 'timezone', 'email', 'phone',
  'address_line', 'city', 'state', 'postal_code', 'country',
];

const toForm = (business) =>
  Object.fromEntries(PROFILE_FIELDS.map((field) => [field, business[field] ?? '']));

function ProfileForm({ business, canEdit, onSaved }) {
  const { notifySuccess } = useSnackbar();
  const [form, setForm] = useState(() => toForm(business));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const timezones = useMemo(listTimezones, []);

  useEffect(() => setForm(toForm(business)), [business]);

  const handleChange = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    // Empty optional fields are sent as null so they are cleared on the server.
    const payload = Object.fromEntries(
      PROFILE_FIELDS.map((field) => [field, typeof form[field] === 'string' ? form[field].trim() || null : form[field]]),
    );
    try {
      onSaved(await businessApi.update(business.id, payload));
      notifySuccess('Business profile saved.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const field = (name, label, props = {}) => (
    <TextField name={name} label={label} value={form[name]} onChange={handleChange} disabled={!canEdit} {...props} />
  );

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <ErrorAlert message={error} />
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Details
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, mb: 3 }}>
        {field('name', 'Business name', { required: true })}
        <SelectField name="category" label="Category" value={form.category} onChange={handleChange}
          options={BUSINESS_CATEGORIES} disabled={!canEdit} />
        <Box sx={{ gridColumn: { sm: 'span 2' } }}>
          {field('description', 'Description', { multiline: true, minRows: 3 })}
        </Box>
        <Autocomplete
          options={timezones}
          value={form.timezone}
          disableClearable
          disabled={!canEdit}
          onChange={(_event, value) => setForm({ ...form, timezone: value })}
          renderInput={(params) => <TextField {...params} label="Timezone" />}
        />
      </Box>

      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Contact & address
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
        {field('email', 'Contact email', { type: 'email' })}
        {field('phone', 'Contact phone')}
        <Box sx={{ gridColumn: { sm: 'span 2' } }}>{field('address_line', 'Street address')}</Box>
        {field('city', 'City')}
        {field('state', 'State / region')}
        {field('postal_code', 'Postal code')}
        {field('country', 'Country')}
      </Box>

      {canEdit && (
        <SubmitButton loading={saving} sx={{ mt: 3 }} disabled={form.name.trim().length < 2}>
          Save profile
        </SubmitButton>
      )}
    </Box>
  );
}

function HoursForm({ business, canEdit, onSaved }) {
  const { notifySuccess } = useSnackbar();
  const [hours, setHours] = useState(() => toEditorHours(business.working_hours));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => setHours(toEditorHours(business.working_hours)), [business]);

  const handleSave = async () => {
    const validationError = validateHours(hours);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError('');
    setSaving(true);
    try {
      onSaved(await businessApi.updateWorkingHours(business.id, toApiHours(hours)));
      notifySuccess('Working hours saved.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box>
      {business.working_hours.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Working hours are not set yet. A standard weekday schedule is pre-filled below.
        </Alert>
      )}
      <ErrorAlert message={error} />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Times are in the business timezone ({business.timezone}).
      </Typography>
      <WorkingHoursEditor value={hours} onChange={setHours} disabled={!canEdit} />
      {canEdit && (
        <SubmitButton type="button" loading={saving} onClick={handleSave} sx={{ mt: 3 }}>
          Save working hours
        </SubmitButton>
      )}
    </Box>
  );
}

export default function BusinessProfilePage() {
  const { businessId } = useParams();
  const { notifySuccess, notifyError } = useSnackbar();
  const access = useBusinessAccess(businessId);
  const { data: business, loading, error, reload, setData } = useAsync(() => businessApi.get(businessId), [businessId]);
  const [tab, setTab] = useState('profile');
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);

  if ((loading && !business) || access.loading) return <LoadingScreen message="Loading business…" />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  if (!access.isMember) {
    return <Alert severity="warning">You are not a member of this business.</Alert>;
  }

  const toggleStatus = async () => {
    try {
      const updated = await businessApi.setStatus(business.id, !business.is_active);
      setData(updated);
      notifySuccess(updated.is_active ? 'Business activated.' : 'Business deactivated.');
      setStatusDialogOpen(false);
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <>
      <PageHeader
        title={business.name}
        subtitle={
          <Box component="span" sx={{ display: 'inline-flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            Business profile
            {access.role && <Chip size="small" label={`You: ${ROLE_LABELS[access.role]}`} />}
            <Chip size="small" color={business.is_active ? 'success' : 'warning'} label={business.is_active ? 'Active' : 'Inactive'} />
          </Box>
        }
        actions={
          <>
            {access.isOwner && (
              <Button color={business.is_active ? 'warning' : 'success'} variant="contained" onClick={() => setStatusDialogOpen(true)}>
                {business.is_active ? 'Deactivate' : 'Activate'}
              </Button>
            )}
          </>
        }
      />

      <BusinessNav businessId={business.id} canManage={access.canManage} />
      {!business.is_active && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          This business is inactive and hidden from customers.
        </Alert>
      )}
      {!access.canManage && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You have view-only access. Owners and managers can edit this business.
        </Alert>
      )}

      <Card>
        <Tabs value={tab} onChange={(_event, value) => setTab(value)} sx={{ px: 2, borderBottom: 1, borderColor: 'divider' }} variant="scrollable">
          <Tab value="profile" label="Profile" />
          <Tab value="hours" label="Working hours" />
          <Tab value="team" label="Team" />
        </Tabs>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          {tab === 'profile' && <ProfileForm business={business} canEdit={access.canManage} onSaved={setData} />}
          {tab === 'hours' && <HoursForm business={business} canEdit={access.canManage} onSaved={setData} />}
          {tab === 'team' && <MembersPanel businessId={business.id} canEdit={access.isOwner} />}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={statusDialogOpen}
        title={business.is_active ? 'Deactivate business?' : 'Activate business?'}
        message={
          business.is_active
            ? 'Customers will no longer see this business or its services. You can reactivate it at any time.'
            : 'The business and its active services will become visible to customers again.'
        }
        confirmLabel={business.is_active ? 'Deactivate' : 'Activate'}
        confirmColor={business.is_active ? 'warning' : 'success'}
        onConfirm={toggleStatus}
        onClose={() => setStatusDialogOpen(false)}
      />
    </>
  );
}
