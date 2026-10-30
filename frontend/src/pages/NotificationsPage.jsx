import { Box } from '@mui/material';
import NotificationsPanel from '../components/NotificationsPanel';
import PageHeader from '../components/PageHeader';

export default function NotificationsPage() {
  return (
    <Box sx={{ maxWidth: 760 }}>
      <PageHeader title="Notifications" subtitle="Queue, appointment and team updates." />
      <NotificationsPanel limit={50} title="Latest" />
    </Box>
  );
}
