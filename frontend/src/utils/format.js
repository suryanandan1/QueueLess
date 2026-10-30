/** Date/time helpers. Business times are shown in the business's own timezone. */

export function formatDateTime(value, timeZone) {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, {
    timeZone,
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function formatTime(value, timeZone) {
  if (!value) return '—';
  return new Date(value).toLocaleTimeString(undefined, { timeZone, hour: '2-digit', minute: '2-digit' });
}

/** Format a calendar date (YYYY-MM-DD) without shifting it across timezones. */
export function formatDate(isoDate) {
  if (!isoDate) return '—';
  return new Date(`${isoDate}T12:00:00Z`).toLocaleDateString(undefined, { timeZone: 'UTC', dateStyle: 'medium' });
}

/** Today's calendar date (YYYY-MM-DD) in the given IANA timezone. */
export function todayIn(timeZone) {
  return new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(),
  );
}

export function addDays(isoDate, days) {
  const date = new Date(`${isoDate}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function minutesBetween(start, end) {
  if (!start || !end) return null;
  return Math.round((new Date(end) - new Date(start)) / 60000);
}
