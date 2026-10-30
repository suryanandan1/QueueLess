import { describe, expect, it } from 'vitest';
import { defaultWeek, describeDay, toApiHours, toEditorHours, validateHours } from './hours';

describe('working hours helpers', () => {
  it('fills a default week when the API has no hours', () => {
    const week = toEditorHours([]);
    expect(week).toHaveLength(7);
    expect(week[0]).toMatchObject({ is_closed: false, open_time: '09:00', close_time: '17:00' });
    expect(week[6].is_closed).toBe(true);
  });

  it('converts API times and marks missing days as closed', () => {
    const week = toEditorHours([{ day_of_week: 2, is_closed: false, open_time: '08:30:00', close_time: '12:00:00' }]);
    expect(week[2]).toMatchObject({ open_time: '08:30', close_time: '12:00' });
    expect(week[0].is_closed).toBe(true);
  });

  it('sends null times for closed days', () => {
    const api = toApiHours(defaultWeek());
    expect(api[5]).toEqual({ day_of_week: 5, is_closed: true, open_time: null, close_time: null });
  });

  it('rejects opening after closing', () => {
    const week = defaultWeek();
    week[1] = { ...week[1], open_time: '18:00', close_time: '09:00' };
    expect(validateHours(week)).toMatch(/Tuesday/);
    expect(validateHours(defaultWeek())).toBeNull();
  });

  it('describes a day', () => {
    expect(describeDay({ is_closed: true })).toBe('Closed');
    expect(describeDay({ is_closed: false, open_time: '09:00:00', close_time: '17:00:00' })).toBe('09:00 – 17:00');
  });
});
