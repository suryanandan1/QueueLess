import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  Chip,
  IconButton,
  Tooltip,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AddIcon from '@mui/icons-material/Add';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ConfirmDialog from '../../components/ConfirmDialog';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import BusinessNav from '../../components/business/BusinessNav';
import ServiceDetailsPanel from '../../components/services/ServiceDetailsPanel';
import ServiceFormDialog from '../../components/services/ServiceFormDialog';
import { useAsync } from '../../hooks/useAsync';
import { useBusinessAccess } from '../../hooks/useBusinessAccess';
import { useSnackbar } from '../../hooks/useSnackbar';
import { businessApi } from '../../services/businessApi';
import { serviceApi } from '../../services/serviceApi';
import { getErrorMessage } from '../../utils/errors';

export default function ServiceManagementPage() {
  const { businessId } = useParams();
  const { notifySuccess, notifyError } = useSnackbar();
  const access = useBusinessAccess(businessId);
  const { data, loading, error, reload, setData } = useAsync(
    () =>
      Promise.all([businessApi.get(businessId), serviceApi.listForBusiness(businessId, true)]).then(
        ([business, services]) => ({ business, services }),
      ),
    [businessId],
  );
  const [dialog, setDialog] = useState({ open: false, service: null });
  const [deleting, setDeleting] = useState(null);
  const [expanded, setExpanded] = useState(null);

  if ((loading && !data) || access.loading) return <LoadingScreen message="Loading services…" />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;

  const { business, services } = data;
  const canEdit = access.canManage;

  const setServices = (updater) => setData((current) => ({ ...current, services: updater(current.services) }));

  const handleSubmit = async (payload) => {
    if (dialog.service) {
      const updated = await serviceApi.update(dialog.service.id, payload);
      setServices((list) => list.map((s) => (s.id === updated.id ? updated : s)));
      notifySuccess('Service updated.');
    } else {
      const created = await serviceApi.create(business.id, payload);
      setServices((list) => [...list, created].sort((a, b) => a.name.localeCompare(b.name)));
      notifySuccess('Service created.');
    }
    setDialog({ open: false, service: null });
  };

  const toggleActive = async (service) => {
    try {
      const updated = await serviceApi.update(service.id, { is_active: !service.is_active });
      setServices((list) => list.map((s) => (s.id === updated.id ? updated : s)));
      notifySuccess(updated.is_active ? 'Service activated.' : 'Service deactivated.');
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  const confirmDelete = async () => {
    try {
      await serviceApi.remove(deleting.id);
      setServices((list) => list.filter((s) => s.id !== deleting.id));
      notifySuccess('Service deleted.');
      setDeleting(null);
    } catch (err) {
      notifyError(getErrorMessage(err));
      setDeleting(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Services"
        subtitle={business.name}
        actions={
          <>
            {canEdit && (
              <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ open: true, service: null })}>
                New service
              </Button>
            )}
          </>
        }
      />

      <BusinessNav businessId={business.id} canManage={canEdit} />
      {!canEdit && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You have view-only access to services.
        </Alert>
      )}

      {services.length === 0 ? (
        <Card>
          <EmptyState
            title="No services yet"
            description="Add the services customers can queue for, such as “Cash Deposit” or “Haircut”."
            action={
              canEdit && (
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ open: true, service: null })}>
                  Add a service
                </Button>
              )
            }
          />
        </Card>
      ) : (
        services.map((service) => (
          <Accordion
            key={service.id}
            expanded={expanded === service.id}
            onChange={(_event, isOpen) => setExpanded(isOpen ? service.id : null)}
            variant="outlined"
            disableGutters
            sx={{ mb: 1.5, borderRadius: 2, '&:before': { display: 'none' } }}
            slotProps={{ transition: { unmountOnExit: true } }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', width: '100%', pr: 1 }}>
                <Box sx={{ flexGrow: 1, minWidth: 180 }}>
                  <Typography fontWeight={600}>{service.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    ~{service.estimated_duration_minutes} min · {service.max_queue_capacity ? `Max ${service.max_queue_capacity} in queue` : 'No queue limit'}
                    {service.operating_hours ? ' · Custom hours' : ''}
                  </Typography>
                </Box>
                <Chip size="small" color={service.is_active ? 'success' : 'default'} label={service.is_active ? 'Active' : 'Inactive'} />
                <Chip size="small" variant="outlined" label={service.is_available ? 'Available' : 'Paused'} />
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {service.description && (
                <Typography color="text.secondary" sx={{ mb: 2 }}>
                  {service.description}
                </Typography>
              )}
              {canEdit && (
                <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <Button size="small" variant="outlined" startIcon={<EditOutlinedIcon />} onClick={() => setDialog({ open: true, service })}>
                    Edit
                  </Button>
                  <Button size="small" variant="outlined" color={service.is_active ? 'warning' : 'success'} onClick={() => toggleActive(service)}>
                    {service.is_active ? 'Deactivate' : 'Activate'}
                  </Button>
                  <Tooltip title="Delete (only possible if the service has no queue history)">
                    <IconButton size="small" aria-label={`Delete ${service.name}`} onClick={() => setDeleting(service)}>
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              )}
              <ServiceDetailsPanel service={service} />
            </AccordionDetails>
          </Accordion>
        ))
      )}

      <ServiceFormDialog
        open={dialog.open}
        service={dialog.service}
        onClose={() => setDialog({ open: false, service: null })}
        onSubmit={handleSubmit}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete service?"
        message={
          deleting
            ? `“${deleting.name}” and its counters will be permanently deleted. Services with queue history cannot be deleted; deactivate them instead.`
            : ''
        }
        confirmLabel="Delete"
        confirmColor="error"
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}
