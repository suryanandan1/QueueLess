import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Box, Tab, Tabs } from '@mui/material';

const SECTIONS = [
  { path: 'overview', label: 'Overview' },
  { path: 'queues', label: 'Queues' },
  { path: 'appointments', label: 'Appointments' },
  { path: 'services', label: 'Services' },
  { path: 'counters', label: 'Counters' },
  { path: 'profile', label: 'Profile & team' },
  { path: 'analytics', label: 'Analytics', managersOnly: true },
];

/** Section tabs shared by every business management page. */
export default function BusinessNav({ businessId, canManage }) {
  const { pathname } = useLocation();
  const base = `/businesses/${businessId}`;
  const sections = SECTIONS.filter((section) => canManage || !section.managersOnly);
  const current = sections.find((section) => pathname.startsWith(`${base}/${section.path}`))?.path ?? false;

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
      <Tabs value={current} variant="scrollable" scrollButtons="auto" aria-label="Business sections">
        {sections.map((section) => (
          <Tab
            key={section.path}
            value={section.path}
            label={section.label}
            component={RouterLink}
            to={`${base}/${section.path}`}
          />
        ))}
      </Tabs>
    </Box>
  );
}
