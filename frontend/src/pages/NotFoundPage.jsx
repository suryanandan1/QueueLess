import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Typography } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { HOME_PATH_BY_ROLE } from '../utils/constants';

export default function NotFoundPage() {
  const { user } = useAuth();
  const home = user ? HOME_PATH_BY_ROLE[user.role] : '/login';
  return (
    <Box sx={{ minHeight: '70vh', display: 'grid', placeItems: 'center', textAlign: 'center', px: 2 }}>
      <Box>
        <Typography variant="h2" fontWeight={700} color="primary">
          404
        </Typography>
        <Typography variant="h6" sx={{ mt: 1 }}>
          This page does not exist.
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          The link may be broken or the page may have moved.
        </Typography>
        <Button variant="contained" component={RouterLink} to={home}>
          Go to {user ? 'your dashboard' : 'sign in'}
        </Button>
      </Box>
    </Box>
  );
}
