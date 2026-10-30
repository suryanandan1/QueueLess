import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AuthContext } from '../context/AuthContext';
import ProtectedRoute from './ProtectedRoute';

function renderWithAuth(authValue, initialPath, roles) {
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/login" element={<p>Login page</p>} />
          <Route path="/customer" element={<p>Customer home</p>} />
          <Route element={<ProtectedRoute roles={roles} />}>
            <Route path="/owner" element={<p>Owner dashboard</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('ProtectedRoute', () => {
  it('redirects anonymous users to login', () => {
    renderWithAuth({ user: null, initializing: false }, '/owner', ['BUSINESS_OWNER']);
    expect(screen.getByText('Login page')).toBeInTheDocument();
  });

  it('sends users with the wrong role to their own dashboard', () => {
    renderWithAuth({ user: { role: 'CUSTOMER' }, initializing: false }, '/owner', ['BUSINESS_OWNER']);
    expect(screen.getByText('Customer home')).toBeInTheDocument();
  });

  it('renders the page for an allowed role', () => {
    renderWithAuth({ user: { role: 'BUSINESS_OWNER' }, initializing: false }, '/owner', ['BUSINESS_OWNER']);
    expect(screen.getByText('Owner dashboard')).toBeInTheDocument();
  });

  it('shows a loader while the session is being restored', () => {
    renderWithAuth({ user: null, initializing: true }, '/owner', ['BUSINESS_OWNER']);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
