/** Turn an Axios/FastAPI error into a single human-readable message. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) return fallback;
  const detail = error.response?.data?.detail;

  if (typeof detail === 'string') return detail;

  // FastAPI validation errors: [{ loc: ['body', 'field'], msg: '...' }]
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const message = String(item.msg || '').replace(/^Value error, /, '');
        const field = (item.loc || []).filter((part) => part !== 'body').join('.');
        return field ? `${field}: ${message}` : message;
      })
      .join(' ');
  }

  if (error.request && !error.response) {
    return 'Cannot reach the server. Make sure the backend is running.';
  }
  return error.message || fallback;
}
