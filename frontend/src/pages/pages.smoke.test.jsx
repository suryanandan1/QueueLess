/**
 * Render every page against mocked API responses to catch runtime rendering
 * errors, and check that key actions call the real API functions.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../context/AuthContext';
import { SnackbarProvider } from '../context/SnackbarContext';

const TS = '2026-10-30T10:00:00Z';
const business = {
  id: 1, name: 'Sunrise Salon', slug: 'sunrise-salon', description: 'Hair and spa', category: 'SALON',
  email: null, phone: '+91 99999 00000', address_line: null, city: 'Pune', state: null, postal_code: null,
  country: null, timezone: 'UTC', is_active: true, created_at: TS, updated_at: TS,
  working_hours: [{ day_of_week: 0, is_closed: false, open_time: '09:00:00', close_time: '17:00:00' }],
};
const service = {
  id: 7, business_id: 1, name: 'Haircut', description: null, estimated_duration_minutes: 30, max_queue_capacity: null,
  is_active: true, is_available: true, operating_hours: null, token_prefix: 'A', appointments_enabled: true,
  appointment_duration_minutes: 30, appointment_slot_capacity: 1, appointment_daily_capacity: null,
  appointment_hours: null, created_at: TS, updated_at: TS,
};
const ownerUser = { id: 1, email: 'own@example.com', full_name: 'Olivia Owner', phone: null, role: 'BUSINESS_OWNER', is_active: true, created_at: TS };
const member = { id: 3, business_id: 1, role: 'OWNER', is_active: true, created_at: TS, user: ownerUser };
const estimate = { minutes: 15, people_ahead: 1, average_service_minutes: 30, active_counters: 1, basis: 'configured', note: 'This is an estimate, not a guarantee.' };
const queue = {
  id: 11, business_id: 1, business_name: 'Sunrise Salon', service_id: 7, service_name: 'Haircut', session_date: '2026-10-30',
  status: 'OPEN', max_capacity: null, token_prefix: 'A', tokens_issued: 2, opened_at: TS, paused_at: null, closed_at: null,
  created_at: TS, waiting_count: 1, active_count: 2, is_full: false, accepting_customers: true, not_accepting_reason: null,
  now_serving: [{ display_code: 'A001', counter_name: 'Chair 1', status: 'SERVING' }], estimate_for_new_customer: estimate,
};
const token = (overrides = {}) => ({
  id: 21, display_code: 'A002', token_number: 2, status: 'WAITING', queue_session_id: 11, queue_status: 'OPEN',
  session_date: '2026-10-30', service_id: 7, service_name: 'Haircut', business_id: 1, business_name: 'Sunrise Salon',
  customer_id: 5, customer_name: 'Cara Customer', is_walk_in: false, counter_id: null, counter_name: null, recall_count: 0,
  joined_at: TS, called_at: null, service_started_at: null, completed_at: null, skipped_at: null, no_show_at: null,
  cancelled_at: null, position: 1, estimate, customer_phone: null, customer_email: 'cara@example.com', ...overrides,
});
const counter = {
  id: 4, service_id: 7, service_name: 'Haircut', business_id: 1, name: 'Chair 1', is_active: true, status: 'BUSY',
  assigned_member_id: 3, assigned_member_name: 'Olivia Owner', current_token: { id: 20, display_code: 'A001', status: 'SERVING' },
  created_at: TS, updated_at: TS,
};
const appointment = {
  id: 31, service_id: 7, service_name: 'Haircut', business_id: 1, business_name: 'Sunrise Salon', business_timezone: 'UTC',
  customer_id: 5, customer_name: 'Cara Customer', customer_email: 'cara@example.com', customer_phone: null,
  scheduled_start: '2099-01-01T10:00:00Z', scheduled_end: '2099-01-01T10:30:00Z', status: 'BOOKED', notes: null,
  cancellation_reason: null, created_at: TS, confirmed_at: null, checked_in_at: null, completed_at: null, cancelled_at: null,
};
const page = (items) => ({ items, total: items.length, limit: 20, offset: 0 });

vi.mock('../services/businessApi', () => ({
  businessApi: {
    list: vi.fn(async () => page([business])),
    mine: vi.fn(async () => [{ membership_id: 3, role: 'OWNER', business }]),
    get: vi.fn(async () => business),
    stats: vi.fn(async () => ({ business_id: 1, total_services: 1, active_services: 1, total_counters: 1, active_counters: 1, active_members: 2, tokens_today: 2, tokens_waiting: 1, tokens_completed_today: 0, upcoming_appointments: 1 })),
    analytics: vi.fn(async () => ({
      business_id: 1, start_date: '2026-10-24', end_date: '2026-10-30', total_tokens: 2, completion_rate: 0.5, no_show_rate: 0.5,
      days: [{ date: '2026-10-30', tokens_issued: 2, completed: 1, cancelled: 0, no_show: 1, average_wait_minutes: 4, average_service_minutes: 12 }],
      services: [{ service_id: 7, service_name: 'Haircut', tokens_issued: 2, completed: 1, average_wait_minutes: 4, average_service_minutes: 12 }],
      appointments: { total: 1, completed: 0, cancelled: 0, no_show: 0, upcoming: 1 },
    })),
  },
  memberApi: { list: vi.fn(async () => [member]) },
}));
vi.mock('../services/serviceApi', () => ({
  serviceApi: {
    listForBusiness: vi.fn(async () => [service]),
    get: vi.fn(async () => service),
    stats: vi.fn(async () => ({ service_id: 7, total_counters: 1, active_counters: 1, tokens_today: 2, tokens_waiting: 1, tokens_completed_today: 0, average_service_minutes: null, upcoming_appointments: 0 })),
  },
}));
vi.mock('../services/counterApi', () => ({
  counterApi: {
    forBusiness: vi.fn(async () => [counter]),
    forService: vi.fn(async () => [counter]),
    assigned: vi.fn(async () => [counter]),
    console: vi.fn(async () => ({
      counter, queue,
      current_token: token({ id: 20, display_code: 'A001', status: 'SERVING', counter_id: 4, counter_name: 'Chair 1', called_at: TS, service_started_at: TS }),
      waiting: [token()], skipped: [], recently_completed: [],
    })),
    callNext: vi.fn(async () => token({ status: 'CALLED' })),
  },
}));
vi.mock('../services/queueApi', () => ({
  queueApi: {
    listActive: vi.fn(async () => [queue]),
    get: vi.fn(async () => queue),
    tokens: vi.fn(async () => [token(), token({ id: 20, display_code: 'A001', status: 'SERVING', counter_name: 'Chair 1' })]),
    forBusiness: vi.fn(async () => page([queue])),
    join: vi.fn(async () => token()),
  },
  tokenApi: {
    mine: vi.fn(async () => page([token()])),
    get: vi.fn(async () => token()),
    complete: vi.fn(async () => token({ status: 'COMPLETED' })),
  },
}));
vi.mock('../services/appointmentApi', () => ({
  appointmentApi: {
    mine: vi.fn(async () => page([appointment])),
    forBusiness: vi.fn(async () => page([appointment])),
    slots: vi.fn(async () => ({
      service_id: 7, date: '2099-01-01', timezone: 'UTC', duration_minutes: 30, daily_capacity: null, daily_remaining: null,
      slots: [
        { start: '2099-01-01T10:00:00Z', end: '2099-01-01T10:30:00Z', remaining: 1, is_available: true },
        { start: '2099-01-01T10:30:00Z', end: '2099-01-01T11:00:00Z', remaining: 0, is_available: false },
      ],
    })),
    book: vi.fn(async () => appointment),
  },
}));
vi.mock('../services/notificationApi', () => ({
  notificationApi: {
    list: vi.fn(async () => page([{ id: 1, business_id: 1, type: 'QUEUE_UPDATE', title: 'Token A002 confirmed', message: 'You joined', is_read: false, read_at: null, created_at: TS }])),
    unreadCount: vi.fn(async () => ({ unread: 1 })),
  },
}));
vi.mock('../services/adminApi', () => ({
  adminApi: {
    stats: vi.fn(async () => ({ total_users: 2, active_users: 2, users_by_role: { SUPER_ADMIN: 1, BUSINESS_OWNER: 1, STAFF: 0, CUSTOMER: 0 }, total_businesses: 1, active_businesses: 1, total_services: 1, tokens_today: 0 })),
    listUsers: vi.fn(async () => page([ownerUser])),
  },
}));

let pages;
let apis;
beforeAll(async () => {
  // jsdom has no WebSocket server; live updates fall back to polling.
  globalThis.WebSocket = class { close() {} };
  pages = {
    CustomerDashboard: (await import('./customer/CustomerDashboard')).default,
    BusinessDetailsPage: (await import('./customer/BusinessDetailsPage')).default,
    TokenTrackingPage: (await import('./customer/TokenTrackingPage')).default,
    MyTokensPage: (await import('./customer/MyTokensPage')).default,
    MyAppointmentsPage: (await import('./customer/MyAppointmentsPage')).default,
    BookAppointmentPage: (await import('./customer/BookAppointmentPage')).default,
    OwnerDashboard: (await import('./owner/OwnerDashboard')).default,
    StaffDashboard: (await import('./staff/StaffDashboard')).default,
    CounterConsolePage: (await import('./staff/CounterConsolePage')).default,
    BusinessOverviewPage: (await import('./business/BusinessOverviewPage')).default,
    QueuesPage: (await import('./business/QueuesPage')).default,
    QueueMonitorPage: (await import('./business/QueueMonitorPage')).default,
    AppointmentsManagePage: (await import('./business/AppointmentsManagePage')).default,
    CountersPage: (await import('./business/CountersPage')).default,
    AnalyticsPage: (await import('./business/AnalyticsPage')).default,
    BusinessProfilePage: (await import('./business/BusinessProfilePage')).default,
    ServiceManagementPage: (await import('./business/ServiceManagementPage')).default,
    AdminDashboard: (await import('./admin/AdminDashboard')).default,
    AccountPage: (await import('./AccountPage')).default,
    NotificationsPage: (await import('./NotificationsPage')).default,
  };
  apis = {
    queueApi: (await import('../services/queueApi')).queueApi,
    tokenApi: (await import('../services/queueApi')).tokenApi,
    counterApi: (await import('../services/counterApi')).counterApi,
    appointmentApi: (await import('../services/appointmentApi')).appointmentApi,
  };
});

function renderPage(Page, { path = '/page', url = '/page', user = ownerUser } = {}) {
  return render(
    <AuthContext.Provider value={{ user, setUser: vi.fn(), initializing: false }}>
      <SnackbarProvider>
        <MemoryRouter initialEntries={[url]}>
          <Routes>
            <Route path={path} element={<Page />} />
            <Route path="/my/tokens/:tokenId" element={<p>Token page</p>} />
            <Route path="/my/appointments" element={<p>Appointments list</p>} />
          </Routes>
        </MemoryRouter>
      </SnackbarProvider>
    </AuthContext.Provider>,
  );
}

const businessRoute = { path: '/businesses/:businessId/x', url: '/businesses/1/x' };
const customer = { ...ownerUser, role: 'CUSTOMER' };

describe('customer pages', () => {
  it('dashboard shows active tokens, appointments and businesses', async () => {
    renderPage(pages.CustomerDashboard, { user: customer });
    expect(await screen.findByText('Your active tokens')).toBeInTheDocument();
    expect(await screen.findByText('Upcoming appointments')).toBeInTheDocument();
    expect(await screen.findAllByText('Sunrise Salon', { exact: false })).not.toHaveLength(0);
  });

  it('business details shows the live queue and joins it', async () => {
    renderPage(pages.BusinessDetailsPage, { path: '/b/:businessId', url: '/b/1', user: customer });
    expect(await screen.findByText('Haircut')).toBeInTheDocument();
    expect(screen.getByText(/About 15 min/)).toBeInTheDocument();
    expect(screen.getAllByText('(estimate)').length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /join queue/i }));
    await userEvent.click(await screen.findByRole('button', { name: /get my token/i }));
    expect(apis.queueApi.join).toHaveBeenCalledWith(11);
    expect(await screen.findByText('Token page')).toBeInTheDocument();
  });

  it('token page shows code, position and estimate', async () => {
    renderPage(pages.TokenTrackingPage, { path: '/t/:tokenId', url: '/t/21', user: customer });
    expect(await screen.findByText('A002')).toBeInTheDocument();
    expect(screen.getByText('Your position')).toBeInTheDocument();
    expect(screen.getByText(/A001 at Chair 1/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel token/i })).toBeInTheDocument();
  });

  it('token history and appointments render', async () => {
    renderPage(pages.MyTokensPage, { user: customer });
    expect(await screen.findByText('A002')).toBeInTheDocument();
    renderPage(pages.MyAppointmentsPage, { user: customer });
    expect(await screen.findByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
  });

  it('booking page books the chosen slot', async () => {
    renderPage(pages.BookAppointmentPage, { path: '/book/:serviceId', url: '/book/7', user: customer });
    const slotButtons = await screen.findAllByRole('button', { name: /\d{2}:\d{2}/ });
    expect(slotButtons[1]).toBeDisabled(); // fully booked slot
    await userEvent.click(slotButtons[0]);
    await userEvent.click(screen.getByRole('button', { name: /^book /i }));
    expect(apis.appointmentApi.book).toHaveBeenCalledWith(
      expect.objectContaining({ service_id: 7, scheduled_start: '2099-01-01T10:00:00Z' }),
    );
    expect(await screen.findByText('Appointments list')).toBeInTheDocument();
  });
});

describe('staff pages', () => {
  it('staff dashboard lists assigned counters', async () => {
    renderPage(pages.StaffDashboard, { user: { ...ownerUser, role: 'STAFF' } });
    expect(await screen.findByRole('link', { name: /open console/i })).toBeInTheDocument();
  });

  it('counter console shows the current token and completes it', async () => {
    renderPage(pages.CounterConsolePage, { path: '/c/:counterId', url: '/c/4' });
    expect(await screen.findByText('A001')).toBeInTheDocument();
    expect(screen.getByText(/1\. A002/)).toBeInTheDocument();
    // Calling is disabled while the counter is busy.
    expect(screen.getByRole('button', { name: /call next/i })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: /complete service/i }));
    await waitFor(() => expect(apis.tokenApi.complete).toHaveBeenCalledWith(20));
  });
});

describe('business pages', () => {
  it.each([
    ['BusinessOverviewPage', 'Live queues'],
    ['QueuesPage', "Today's queues"],
    ['AppointmentsManagePage', 'Cara Customer'],
    ['CountersPage', 'Chair 1'],
    ['AnalyticsPage', 'By service'],
  ])('%s renders', async (name, text) => {
    renderPage(pages[name], businessRoute);
    expect(await screen.findByText(text)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument();
  });

  it('queue monitor lists tokens', async () => {
    renderPage(pages.QueueMonitorPage, { path: '/businesses/:businessId/queues/:queueId', url: '/businesses/1/queues/11' });
    expect(await screen.findAllByText('Cara Customer')).toHaveLength(2);
    expect(screen.getByRole('button', { name: /issue token/i })).toBeInTheDocument();
  });

  it('owner pages render', async () => {
    renderPage(pages.OwnerDashboard);
    expect(await screen.findByText('Sunrise Salon')).toBeInTheDocument();
    renderPage(pages.BusinessProfilePage, businessRoute);
    expect(await screen.findByRole('button', { name: /save profile/i })).toBeInTheDocument();
    renderPage(pages.ServiceManagementPage, businessRoute);
    expect(await screen.findByRole('button', { name: /new service/i })).toBeInTheDocument();
  });
});

describe('shared pages', () => {
  it('admin, account and notifications render', async () => {
    renderPage(pages.AdminDashboard, { user: { ...ownerUser, id: 99, role: 'SUPER_ADMIN' } });
    expect(await screen.findByText('own@example.com')).toBeInTheDocument();
    renderPage(pages.AccountPage);
    expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument();
    renderPage(pages.NotificationsPage);
    expect(await screen.findByText('Token A002 confirmed')).toBeInTheDocument();
  });
});
