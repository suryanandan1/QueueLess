import { DAY_NAMES } from './constants';

const trimSeconds = (time) => (time ? time.slice(0, 5) : '');

/** Default schedule used when a business has not configured hours yet: Mon-Fri 09:00-17:00. */
export function defaultWeek() {
  return DAY_NAMES.map((_, day) => ({
    day_of_week: day,
    is_closed: day >= 5,
    open_time: day >= 5 ? '' : '09:00',
    close_time: day >= 5 ? '' : '17:00',
  }));
}

/** Convert API hours (possibly partial) to a full 7-day editor model. */
export function toEditorHours(apiHours) {
  if (!apiHours || apiHours.length === 0) return defaultWeek();
  return DAY_NAMES.map((_, day) => {
    const entry = apiHours.find((item) => item.day_of_week === day);
    if (!entry) return { day_of_week: day, is_closed: true, open_time: '', close_time: '' };
    return {
      day_of_week: day,
      is_closed: entry.is_closed,
      open_time: trimSeconds(entry.open_time),
      close_time: trimSeconds(entry.close_time),
    };
  });
}

export function toApiHours(editorHours) {
  return editorHours.map((day) => ({
    day_of_week: day.day_of_week,
    is_closed: day.is_closed,
    open_time: day.is_closed ? null : day.open_time,
    close_time: day.is_closed ? null : day.close_time,
  }));
}

/** Return an error message for the first invalid day, or null. */
export function validateHours(editorHours) {
  for (const day of editorHours) {
    if (day.is_closed) continue;
    const name = DAY_NAMES[day.day_of_week];
    if (!day.open_time || !day.close_time) return `${name}: set both opening and closing time.`;
    if (day.open_time >= day.close_time) return `${name}: opening time must be before closing time.`;
  }
  return null;
}

export function describeDay(entry) {
  if (!entry || entry.is_closed) return 'Closed';
  return `${trimSeconds(entry.open_time)} – ${trimSeconds(entry.close_time)}`;
}

export function listTimezones() {
  try {
    const zones = Intl.supportedValuesOf('timeZone');
    return zones.includes('UTC') ? zones : ['UTC', ...zones];
  } catch {
    return ['UTC'];
  }
}
