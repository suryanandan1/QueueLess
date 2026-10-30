import { Box, FormControlLabel, Switch, TextField, Typography } from '@mui/material';
import { DAY_NAMES } from '../../utils/constants';

/** Controlled weekly schedule editor. `value` is the 7-day model from utils/hours. */
export default function WorkingHoursEditor({ value, onChange, disabled = false }) {
  const updateDay = (dayIndex, patch) => {
    onChange(value.map((day) => (day.day_of_week === dayIndex ? { ...day, ...patch } : day)));
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {value.map((day) => (
        <Box
          key={day.day_of_week}
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr 1fr', sm: '120px 110px 1fr 1fr' },
            alignItems: 'center',
            gap: 1.5,
          }}
        >
          <Typography fontWeight={500}>{DAY_NAMES[day.day_of_week]}</Typography>
          <FormControlLabel
            label={day.is_closed ? 'Closed' : 'Open'}
            control={
              <Switch
                checked={!day.is_closed}
                disabled={disabled}
                onChange={(event) =>
                  updateDay(day.day_of_week, {
                    is_closed: !event.target.checked,
                    open_time: day.open_time || '09:00',
                    close_time: day.close_time || '17:00',
                  })
                }
              />
            }
          />
          <TextField
            type="time"
            label="Opens"
            value={day.open_time}
            disabled={disabled || day.is_closed}
            onChange={(event) => updateDay(day.day_of_week, { open_time: event.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            type="time"
            label="Closes"
            value={day.close_time}
            disabled={disabled || day.is_closed}
            onChange={(event) => updateDay(day.day_of_week, { close_time: event.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Box>
      ))}
    </Box>
  );
}
