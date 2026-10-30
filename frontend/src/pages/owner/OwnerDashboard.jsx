import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Card } from '@mui/material';
import AddBusinessOutlinedIcon from '@mui/icons-material/AddBusinessOutlined';
import BusinessSummaryCard from '../../components/business/BusinessSummaryCard';
import CreateBusinessDialog from '../../components/business/CreateBusinessDialog';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import { useAsync } from '../../hooks/useAsync';
import { useSnackbar } from '../../hooks/useSnackbar';
import { businessApi } from '../../services/businessApi';

export default function OwnerDashboard() {
  const navigate = useNavigate();
  const { notifySuccess } = useSnackbar();
  const [createOpen, setCreateOpen] = useState(false);
  const { data: memberships, loading, error, reload } = useAsync(() => businessApi.mine(), []);

  const handleCreated = (business) => {
    setCreateOpen(false);
    notifySuccess(`${business.name} was created.`);
    navigate(`/businesses/${business.id}/services`);
  };

  const createButton = (
    <Button variant="contained" startIcon={<AddBusinessOutlinedIcon />} onClick={() => setCreateOpen(true)}>
      New business
    </Button>
  );

  return (
    <>
      <PageHeader title="My businesses" subtitle="Manage your locations, services and team." actions={createButton} />
      <ErrorAlert message={error} onRetry={reload} />

      {loading && !memberships ? (
        <LoadingScreen message="Loading your businesses…" />
      ) : memberships?.length === 0 ? (
        <Card>
          <EmptyState
            title="You have not created a business yet"
            description="Create your first business to start adding services and staff."
            action={createButton}
          />
        </Card>
      ) : (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
          {memberships?.map(({ business, role }) => (
            <BusinessSummaryCard key={business.id} business={business} role={role} />
          ))}
        </Box>
      )}

      <CreateBusinessDialog open={createOpen} onClose={() => setCreateOpen(false)} onCreated={handleCreated} />
    </>
  );
}
