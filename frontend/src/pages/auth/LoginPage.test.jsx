import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../../context/AuthContext';
import LoginPage from './LoginPage';

function renderLogin(login) {
  return render(
    <AuthContext.Provider value={{ login }}>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/owner" element={<p>Owner dashboard</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('LoginPage', () => {
  it('logs in and navigates to the role dashboard', async () => {
    const login = vi.fn().mockResolvedValue({ role: 'BUSINESS_OWNER' });
    renderLogin(login);

    await userEvent.type(screen.getByLabelText(/email/i), 'owner@example.com');
    await userEvent.type(screen.getByLabelText(/^password/i), 'Passw0rd!');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(login).toHaveBeenCalledWith('owner@example.com', 'Passw0rd!');
    expect(await screen.findByText('Owner dashboard')).toBeInTheDocument();
  });

  it('shows the API error for invalid credentials', async () => {
    const login = vi.fn().mockRejectedValue({ response: { data: { detail: 'Invalid email or password.' } } });
    renderLogin(login);

    await userEvent.type(screen.getByLabelText(/email/i), 'x@example.com');
    await userEvent.type(screen.getByLabelText(/^password/i), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument();
  });
});
