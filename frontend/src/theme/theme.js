import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1e5eff', dark: '#1544c4', light: '#e8efff' },
    secondary: { main: '#0f9d76' },
    background: { default: '#f5f7fb', paper: '#ffffff' },
    text: { primary: '#14213d', secondary: '#5b6475' },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiCard: {
      defaultProps: { variant: 'outlined' },
      styleOverrides: { root: { borderColor: '#e3e8f2' } },
    },
    MuiPaper: { styleOverrides: { outlined: { borderColor: '#e3e8f2' } } },
    MuiTextField: { defaultProps: { size: 'small', fullWidth: true } },
    MuiSelect: { defaultProps: { size: 'small' } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 600, color: '#5b6475' } } },
  },
});

export default theme;
