import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  Chip,
  InputAdornment,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Tabs,
  TextField,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import EmptyState from '../../components/EmptyState';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import PageHeader from '../../components/PageHeader';
import StatCard, { StatGrid } from '../../components/StatCard';
import SelectField from '../../components/forms/SelectField';
import { useAsync } from '../../hooks/useAsync';
import { useAuth } from '../../hooks/useAuth';
import { useDebounced } from '../../hooks/useDebounced';
import { useSnackbar } from '../../hooks/useSnackbar';
import { adminApi } from '../../services/adminApi';
import { businessApi } from '../../services/businessApi';
import { ROLE_LABELS, ROLES, categoryLabel } from '../../utils/constants';
import { getErrorMessage } from '../../utils/errors';

const ROLE_OPTIONS = Object.values(ROLES).map((role) => ({ value: role, label: ROLE_LABELS[role] }));
const formatDate = (value) => new Date(value).toLocaleString();

/** Server-paginated table state shared by the admin tabs. */
function usePagedQuery(fetchPage, filters) {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const filterKey = JSON.stringify(filters);

  useEffect(() => setPage(0), [filterKey]);

  const query = useAsync(
    () => fetchPage({ ...filters, limit: rowsPerPage, offset: page * rowsPerPage }),
    [filterKey, page, rowsPerPage],
  );

  const pagination = (
    <TablePagination
      component="div"
      count={query.data?.total ?? 0}
      page={page}
      rowsPerPage={rowsPerPage}
      rowsPerPageOptions={[10, 25, 50]}
      onPageChange={(_event, value) => setPage(value)}
      onRowsPerPageChange={(event) => {
        setRowsPerPage(Number(event.target.value));
        setPage(0);
      }}
    />
  );
  return { ...query, pagination };
}

function SearchBox({ value, onChange, placeholder }) {
  return (
    <TextField
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      slotProps={{
        input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> },
        htmlInput: { 'aria-label': placeholder },
      }}
    />
  );
}

function UsersTab({ onChanged }) {
  const { user: me } = useAuth();
  const { notifySuccess, notifyError } = useSnackbar();
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const debouncedSearch = useDebounced(search);
  const { data, loading, error, reload, setData, pagination } = usePagedQuery(adminApi.listUsers, {
    search: debouncedSearch.trim() || undefined,
    role: role || undefined,
  });

  const toggle = async (user) => {
    try {
      const updated = await adminApi.setUserStatus(user.id, !user.is_active);
      setData((current) => ({ ...current, items: current.items.map((u) => (u.id === updated.id ? updated : u)) }));
      notifySuccess(`${updated.email} ${updated.is_active ? 'activated' : 'deactivated'}.`);
      onChanged();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '2fr 1fr' }, gap: 2, p: 2 }}>
        <SearchBox value={search} onChange={setSearch} placeholder="Search by name or email" />
        <SelectField label="Role" value={role} onChange={(event) => setRole(event.target.value)} options={ROLE_OPTIONS} emptyLabel="All roles" />
      </Box>
      <ErrorAlert message={error} onRetry={reload} sx={{ mx: 2 }} />
      {loading && !data ? (
        <LoadingScreen />
      ) : data?.items.length === 0 ? (
        <EmptyState title="No users match these filters" />
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Joined</TableCell>
                <TableCell>Active</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.items.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.full_name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell><Chip size="small" label={ROLE_LABELS[user.role]} /></TableCell>
                  <TableCell>{formatDate(user.created_at)}</TableCell>
                  <TableCell>
                    <Switch
                      checked={user.is_active}
                      disabled={user.id === me.id}
                      onChange={() => toggle(user)}
                      slotProps={{ input: { 'aria-label': `Active status of ${user.email}` } }}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {pagination}
    </>
  );
}

function BusinessesTab({ onChanged }) {
  const { notifySuccess, notifyError } = useSnackbar();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounced(search);
  const { data, loading, error, reload, setData, pagination } = usePagedQuery(adminApi.listBusinesses, {
    search: debouncedSearch.trim() || undefined,
  });

  const toggle = async (business) => {
    try {
      const updated = await businessApi.setStatus(business.id, !business.is_active);
      setData((current) => ({ ...current, items: current.items.map((b) => (b.id === updated.id ? updated : b)) }));
      notifySuccess(`${updated.name} ${updated.is_active ? 'activated' : 'deactivated'}.`);
      onChanged();
    } catch (err) {
      notifyError(getErrorMessage(err));
    }
  };

  return (
    <>
      <Box sx={{ p: 2 }}>
        <SearchBox value={search} onChange={setSearch} placeholder="Search businesses" />
      </Box>
      <ErrorAlert message={error} onRetry={reload} sx={{ mx: 2 }} />
      {loading && !data ? (
        <LoadingScreen />
      ) : data?.items.length === 0 ? (
        <EmptyState title="No businesses found" />
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>City</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Active</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.items.map((business) => (
                <TableRow key={business.id}>
                  <TableCell>{business.name}</TableCell>
                  <TableCell>{categoryLabel(business.category)}</TableCell>
                  <TableCell>{business.city || '—'}</TableCell>
                  <TableCell>{formatDate(business.created_at)}</TableCell>
                  <TableCell>
                    <Switch
                      checked={business.is_active}
                      onChange={() => toggle(business)}
                      slotProps={{ input: { 'aria-label': `Active status of ${business.name}` } }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button size="small" component={RouterLink} to={`/businesses/${business.id}/overview`}>
                      Manage
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {pagination}
    </>
  );
}

function AuditTab() {
  const { data, loading, error, reload, pagination } = usePagedQuery(adminApi.listAuditLogs, {});
  return (
    <>
      <ErrorAlert message={error} onRetry={reload} sx={{ m: 2 }} />
      {loading && !data ? (
        <LoadingScreen />
      ) : data?.items.length === 0 ? (
        <EmptyState title="No audit entries yet" />
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>When</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Actor</TableCell>
                <TableCell>Business</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>IP</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.items.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>{formatDate(entry.created_at)}</TableCell>
                  <TableCell><code>{entry.action}</code></TableCell>
                  <TableCell>{entry.actor_user_id ?? '—'}</TableCell>
                  <TableCell>{entry.business_id ?? '—'}</TableCell>
                  <TableCell>{entry.entity_type ? `${entry.entity_type} #${entry.entity_id}` : '—'}</TableCell>
                  <TableCell>{entry.ip_address ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {pagination}
    </>
  );
}

export default function AdminDashboard() {
  const [tab, setTab] = useState('users');
  const stats = useAsync(() => adminApi.stats(), []);

  return (
    <>
      <PageHeader title="Platform administration" subtitle="Users, businesses and activity across QueueLess." />
      <ErrorAlert message={stats.error} onRetry={stats.reload} />
      {stats.data && (
        <StatGrid>
          <StatCard label="Users" value={stats.data.total_users} hint={`${stats.data.active_users} active`} />
          <StatCard label="Customers" value={stats.data.users_by_role.CUSTOMER} />
          <StatCard label="Business owners" value={stats.data.users_by_role.BUSINESS_OWNER} />
          <StatCard label="Staff" value={stats.data.users_by_role.STAFF} />
          <StatCard label="Businesses" value={stats.data.total_businesses} hint={`${stats.data.active_businesses} active`} />
          <StatCard label="Services" value={stats.data.total_services} />
          <StatCard label="Tokens today" value={stats.data.tokens_today} hint="UTC date" />
        </StatGrid>
      )}

      <Card>
        <Tabs value={tab} onChange={(_event, value) => setTab(value)} sx={{ px: 2, borderBottom: 1, borderColor: 'divider' }} variant="scrollable">
          <Tab value="users" label="Users" />
          <Tab value="businesses" label="Businesses" />
          <Tab value="audit" label="Audit log" />
        </Tabs>
        {tab === 'users' && <UsersTab onChanged={stats.reload} />}
        {tab === 'businesses' && <BusinessesTab onChanged={stats.reload} />}
        {tab === 'audit' && <AuditTab />}
      </Card>
    </>
  );
}
