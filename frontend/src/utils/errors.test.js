import { describe, expect, it } from 'vitest';
import { getErrorMessage } from './errors';

describe('getErrorMessage', () => {
  it('uses a string detail from the API', () => {
    expect(getErrorMessage({ response: { data: { detail: 'Invalid email or password.' } } })).toBe(
      'Invalid email or password.',
    );
  });

  it('flattens FastAPI validation errors', () => {
    const error = {
      response: {
        data: { detail: [{ loc: ['body', 'password'], msg: 'Value error, Password must be at least 8 characters long.' }] },
      },
    };
    expect(getErrorMessage(error)).toBe('password: Password must be at least 8 characters long.');
  });

  it('reports network failures', () => {
    expect(getErrorMessage({ request: {}, message: 'Network Error' })).toMatch(/Cannot reach the server/);
  });
});
