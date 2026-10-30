import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Pagination,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import StatusChip from '../../components/StatusChip';
import { useAsync } from '../../hooks/useAsync';
import { tokenApi } from '../../services/queueApi';
import { formatDate, formatTime } from '../../utils/format';

const PAGE_SIZE = 10;

export function TokenCard({ token }) {
  return (
    <Card>
      <CardActionArea component={RouterLink} to={`/my/tokens/${token.id}`}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h5" fontWeight={700} color="primary" sx={{ minWidth: 80 }}>
            {token.display_code}
          </Typography>
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography fontWeight={600} noWrap>
              {token.service_name} · {token.business_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatDate(token.session_date)} · joined {formatTime(token.joined_at)}
              {token.position ? ` · number ${token.position} in line` : ''}
            </Typography>
          </Box>
          <StatusChip status={token.status} />
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

export default function MyTokensPage() {
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => tokenApi.mine({ active_only: filter === 'active', limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    [filter, page],
  );
  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader title="My tokens" subtitle="Your queue tokens, current and past." />
      <ToggleButtonGroup value={filter} exclusive size="small" color="primary" sx={{ mb: 2 }}
        onChange={(_e, value) => { if (value) { setFilter(value); setPage(1); } }}>
        <ToggleButton value="all">All</ToggleButton>
        <ToggleButton value="active">Active</ToggleButton>
      </ToggleButtonGroup>
      <ErrorAlert message={error} onRetry={reload} />
      {loading && !data ? (
        <LoadingScreen />
      ) : data?.items.length === 0 ? (
        <Card>
          <EmptyState title="No tokens yet" description="Find a business and join its queue to get a token." />
        </Card>
      ) : (
        <Box sx={{ display: 'grid', gap: 1.5 }}>
          {data?.items.map((token) => <TokenCard key={token.id} token={token} />)}
        </Box>
      )}
      {pageCount > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination count={pageCount} page={page} onChange={(_e, value) => setPage(value)} color="primary" />
        </Box>
      )}
    </>
  );
}
