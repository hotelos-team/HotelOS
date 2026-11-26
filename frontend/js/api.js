const API_BASE = (import.meta.env.VITE_API_URL || 'https://hotelos-w18l.onrender.com').replace(/\/+$/, '');

function apiUrl(path) {
  return `${API_BASE}/${String(path).replace(/^\/+/, '')}`;
}

async function request(path, { method = 'GET', body, role, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (role) headers['X-Role'] = role;
  let response;
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Can’t reach HotelOS. Check that the backend is running and the API URL is correct.');
  }
  const raw = await response.text();
  let data;
  try { data = raw ? JSON.parse(raw) : null; } catch { data = raw; }
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.at(-1) || 'Field'}: ${item.msg}`).join(' · ')
      : (detail || data?.message || `Request failed (${response.status})`);
    throw new Error(message);
  }
  return data;
}

const enc = (value) => encodeURIComponent(value);
export const api = {
  health: () => request('/health'),
  register: (payload) => request('/api/prebook/register', { method: 'POST', body: payload }),
  login: (payload) => request('/api/prebook/login', { method: 'POST', body: payload }),
  staffLogin: (role, password) => request(`/${enc(role)}/${enc(password)}`),
  quote: ({ room_type, check_in, check_out }) => request(`/pricing/quote?${new URLSearchParams({ room_type, check_in, check_out })}`),
  rooms: (role, password) => request(`/rooms/${enc(role)}/${enc(password)}`),
  createBooking: (payload, role = 'customer') => request('/api/bookings/prebook', { method: 'POST', role, body: payload }),
  myBookings: (userId) => request(`/api/bookings/${enc(userId)}`, { role: 'customer' }),
  allBookings: (role, filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.room_id) params.set('room_id', filters.room_id);
    return request(`/api/bookings${params.size ? `?${params}` : ''}`, { role });
  },
  stayAction: (reservationId, action, userId, role) => request(`/api/bookings/${enc(reservationId)}/${action}`, {
    method: 'POST', role, body: { user_id: String(userId) },
  }),
};
