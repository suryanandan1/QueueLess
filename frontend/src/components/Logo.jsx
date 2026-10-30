import { Box, Typography } from '@mui/material';
import FormatListNumberedIcon from '@mui/icons-material/FormatListNumbered';

export default function Logo({ color = 'primary.main' }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <FormatListNumberedIcon sx={{ color }} />
      <Typography variant="h6" component="span" sx={{ color, fontWeight: 700, letterSpacing: 0.3 }}>
        QueueLess
      </Typography>
    </Box>
  );
}
