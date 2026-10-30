import { MenuItem, TextField } from '@mui/material';

/** TextField-based select. `options` is a list of { value, label }. */
export default function SelectField({ options, emptyLabel, ...props }) {
  return (
    <TextField select {...props}>
      {emptyLabel !== undefined && (
        <MenuItem value="">
          <em>{emptyLabel}</em>
        </MenuItem>
      )}
      {options.map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}
