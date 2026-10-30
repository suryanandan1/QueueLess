import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  InputAdornment,
  Pagination,
  TextField,
  Typography,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import NotificationsPanel from '../../components/NotificationsPanel';
import PageHeader from '../../components/PageHeader';
import SelectField from '../../components/forms/SelectField';
import { useAsync } from '../../hooks/useAsync';
import { useAuth } from '../../hooks/useAuth';
import { useDebounced } from '../../hooks/useDebounced';
import { appointmentApi } from '../../services/appointmentApi';
import { businessApi } from '../../services/businessApi';
import { tokenApi } from '../../services/queueApi';
import { AppointmentCard } from './MyAppointmentsPage';
import { TokenCard } from './MyTokensPage';
import { BUSINESS_CATEGORIES, categoryLabel } from '../../utils/constants';

const PAGE_SIZE = 12;

/** Active tokens and the next appointments, shown only when there are any. */
function MyActivity() {
  const { data } = useAsync(
    () =>
      Promise.all([
        tokenApi.mine({ active_only: true, limit: 5 }),
        appointmentApi.mine({ upcoming_only: true, limit: 3 }),
      ]),
    [],
  );
  if (!data) return null;
  const [tokens, appointments] = data;
  if (tokens.items.length === 0 && appointments.items.length === 0) return null;
  return (
    <Box sx={{ display: 'grid', gap: 1.5, mb: 3 }}>
      {tokens.items.length > 0 && <Typography variant="h6">Your active tokens</Typography>}
      {tokens.items.map((token) => <TokenCard key={token.id} token={token} />)}
      {appointments.items.length > 0 && <Typography variant="h6">Upcoming appointments</Typography>}
      {appointments.items.map((appointment) => <AppointmentCard key={appointment.id} appointment={appointment} />)}
    </Box>
  );
}

export default function CustomerDashboard() {
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounced(search);

  useEffect(() => setPage(1), [debouncedSearch, category]);

  const { data, loading, error, reload } = useAsync(
    () =>
      businessApi.list({
        search: debouncedSearch.trim() || undefined,
        category: category || undefined,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
    [debouncedSearch, category, page],
  );

  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader
        title={`Hello, ${user.full_name.split(' ')[0]}`}
        subtitle="Join a queue from anywhere, or book an appointment ahead."
      />

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3, alignItems: 'start' }}>
        <Box>
          <MyActivity />
          <Typography variant="h6" gutterBottom>
            Discover businesses
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '2fr 1fr' }, gap: 2, mb: 2 }}>
            <TextField
              placeholder="Search businesses"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
                htmlInput: { 'aria-label': 'Search businesses' },
              }}
            />
            <SelectField
              label="Category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              options={BUSINESS_CATEGORIES}
              emptyLabel="All categories"
            />
          </Box>

          <ErrorAlert message={error} onRetry={reload} />
          {loading && !data ? (
            <LoadingScreen message="Loading businesses…" />
          ) : data?.items.length === 0 ? (
            <Card>
              <EmptyState title="No businesses found" description="Try a different search or category." />
            </Card>
          ) : (
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, opacity: loading ? 0.6 : 1 }}>
              {data?.items.map((business) => (
                <Card key={business.id}>
                  <CardActionArea component={RouterLink} to={`/explore/businesses/${business.id}`} sx={{ height: '100%' }}>
                    <CardContent>
                      <Chip size="small" label={categoryLabel(business.category)} sx={{ mb: 1 }} />
                      <Typography variant="h6" component="h2">
                        {business.name}
                      </Typography>
                      {business.city && (
                        <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <PlaceOutlinedIcon fontSize="inherit" /> {business.city}
                        </Typography>
                      )}
                      {business.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }} noWrap>
                          {business.description}
                        </Typography>
                      )}
                    </CardContent>
                  </CardActionArea>
                </Card>
              ))}
            </Box>
          )}
          {pageCount > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
              <Pagination count={pageCount} page={page} onChange={(_event, value) => setPage(value)} color="primary" />
            </Box>
          )}
        </Box>

        <NotificationsPanel />
      </Box>
    </>
  );
}
