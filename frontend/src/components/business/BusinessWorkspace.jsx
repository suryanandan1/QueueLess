import { useParams } from 'react-router-dom';
import { Alert } from '@mui/material';
import ErrorAlert from '../ErrorAlert';
import LoadingScreen from '../LoadingScreen';
import PageHeader from '../PageHeader';
import BusinessNav from './BusinessNav';
import { useAsync } from '../../hooks/useAsync';
import { useBusinessAccess } from '../../hooks/useBusinessAccess';
import { businessApi } from '../../services/businessApi';

/**
 * Page shell for business management screens: loads the business and the
 * viewer's role, renders the header and section tabs, then calls
 * `children({ business, access })`.
 */
export default function BusinessWorkspace({ title, actions, children }) {
  const { businessId } = useParams();
  const access = useBusinessAccess(businessId);
  const { data: business, loading, error, reload } = useAsync(() => businessApi.get(businessId), [businessId]);

  if ((loading && !business) || access.loading) return <LoadingScreen />;
  if (error) return <ErrorAlert message={error} onRetry={reload} />;
  if (!access.isMember) return <Alert severity="warning">You are not a member of this business.</Alert>;

  const context = { business, access };
  return (
    <>
      <PageHeader
        title={title}
        subtitle={business.name}
        actions={typeof actions === 'function' ? actions(context) : actions}
      />
      <BusinessNav businessId={business.id} canManage={access.canManage} />
      {!business.is_active && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          This business is inactive and hidden from customers.
        </Alert>
      )}
      {children(context)}
    </>
  );
}
