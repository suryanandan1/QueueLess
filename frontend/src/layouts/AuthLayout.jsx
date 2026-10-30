import { Box, Paper, Typography } from '@mui/material';
import { Outlet } from 'react-router-dom';
import Logo from '../components/Logo';

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: 2,
        py: 4,
        background: 'linear-gradient(160deg, #e8efff 0%, #f5f7fb 55%)',
      }}
    >
      <Box sx={{ width: '100%', maxWidth: 440 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
          <Logo />
        </Box>
        <Paper variant="outlined" sx={{ p: { xs: 3, sm: 4 } }}>
          <Outlet />
        </Paper>
        <Typography variant="caption" color="text.secondary" component="p" align="center" sx={{ mt: 3 }}>
          Skip the line. Join queues remotely and know when it is your turn.
        </Typography>
      </Box>
    </Box>
  );
}
