import { createContext, useCallback, useMemo, useState } from 'react';
import { Alert, Snackbar } from '@mui/material';

export const SnackbarContext = createContext(null);

export function SnackbarProvider({ children }) {
  const [snack, setSnack] = useState(null);

  const notify = useCallback((message, severity = 'success') => {
    setSnack({ message, severity, key: Date.now() });
  }, []);

  const value = useMemo(
    () => ({
      notifySuccess: (message) => notify(message, 'success'),
      notifyError: (message) => notify(message, 'error'),
    }),
    [notify],
  );

  const handleClose = (_event, reason) => {
    if (reason !== 'clickaway') setSnack(null);
  };

  return (
    <SnackbarContext.Provider value={value}>
      {children}
      <Snackbar
        key={snack?.key}
        open={Boolean(snack)}
        autoHideDuration={4000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {snack ? (
          <Alert onClose={handleClose} severity={snack.severity} variant="filled" sx={{ width: '100%' }}>
            {snack.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </SnackbarContext.Provider>
  );
}
