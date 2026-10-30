import { useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import BusinessWorkspace from '../../components/business/BusinessWorkspace';
import ErrorAlert from '../../components/ErrorAlert';
import LoadingScreen from '../../components/LoadingScreen';
import StatCard, { StatGrid } from '../../components/StatCard';
import { useAsync } from '../../hooks/useAsync';
import { businessApi } from '../../services/businessApi';
import { formatDate } from '../../utils/format';

const percent = (value) => (value == null ? '—' : `${Math.round(value * 100)}%`);
const minutes = (value) => (value == null ? '—' : `${value} min`);

function Analytics({ business }) {
  const [days, setDays] = useState(7);
  const { data, loading, error, reload } = useAsync(() => businessApi.analytics(business.id, days), [business.id, days]);

  return (
    <>
      <ToggleButtonGroup value={days} exclusive size="small" color="primary" sx={{ mb: 2 }}
        onChange={(_e, value) => value && setDays(value)}>
        <ToggleButton value={7}>7 days</ToggleButton>
        <ToggleButton value={30}>30 days</ToggleButton>
        <ToggleButton value={90}>90 days</ToggleButton>
      </ToggleButtonGroup>
      <ErrorAlert message={error} onRetry={reload} />
      {loading && !data ? (
        <LoadingScreen />
      ) : data && (
        <>
          <StatGrid>
            <StatCard label="Tokens issued" value={data.total_tokens} />
            <StatCard label="Completion rate" value={percent(data.completion_rate)} hint="of finished tokens" />
            <StatCard label="No-show rate" value={percent(data.no_show_rate)} />
            <StatCard label="Appointments" value={data.appointments.total} hint={`${data.appointments.upcoming} upcoming`} />
            <StatCard label="Appointments completed" value={data.appointments.completed} />
            <StatCard label="Appointment no-shows" value={data.appointments.no_show} />
          </StatGrid>
          {data.total_tokens === 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              No queue activity in this period yet. Figures appear once customers start joining queues.
            </Alert>
          )}

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 3, alignItems: 'start' }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>By service</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Service</TableCell>
                        <TableCell align="right">Tokens</TableCell>
                        <TableCell align="right">Completed</TableCell>
                        <TableCell align="right">Avg. wait</TableCell>
                        <TableCell align="right">Avg. service</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.services.map((row) => (
                        <TableRow key={row.service_id}>
                          <TableCell>{row.service_name}</TableCell>
                          <TableCell align="right">{row.tokens_issued}</TableCell>
                          <TableCell align="right">{row.completed}</TableCell>
                          <TableCell align="right">{minutes(row.average_wait_minutes)}</TableCell>
                          <TableCell align="right">{minutes(row.average_service_minutes)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>By day</Typography>
                <TableContainer sx={{ maxHeight: 420 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        <TableCell align="right">Issued</TableCell>
                        <TableCell align="right">Completed</TableCell>
                        <TableCell align="right">Cancelled</TableCell>
                        <TableCell align="right">No-show</TableCell>
                        <TableCell align="right">Avg. wait</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {[...data.days].reverse().map((row) => (
                        <TableRow key={row.date}>
                          <TableCell>{formatDate(row.date)}</TableCell>
                          <TableCell align="right">{row.tokens_issued}</TableCell>
                          <TableCell align="right">{row.completed}</TableCell>
                          <TableCell align="right">{row.cancelled}</TableCell>
                          <TableCell align="right">{row.no_show}</TableCell>
                          <TableCell align="right">{minutes(row.average_wait_minutes)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Wait = time from joining to being called. Service = time from start to completion.
          </Typography>
        </>
      )}
    </>
  );
}

export default function AnalyticsPage() {
  return <BusinessWorkspace title="Analytics">{(context) => <Analytics {...context} />}</BusinessWorkspace>;
}
