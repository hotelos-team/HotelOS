import { api } from './api.js';
import { dateLabel, escapeHtml as h, money, validateStay } from './format.js';

const app = document.querySelector('#app');
const state = {
  view: 'welcome', user: null, staff: null, staffPassword: '',
  authMode: 'login', authError: '', staffError: '', apiState: 'checking',
  quote: null, quoteError: '', bookingError: '', bookingSuccess: '',
  myBookings: [], myBookingsState: 'idle', bookings: [], bookingsState: 'idle',
  rooms: [], roomsState: 'idle', roomFilter: 'all', statusFilter: '', roomIdFilter: '',
};

const icon = (name) => ({
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  bed: '<path d="M3 18v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6"/><path d="M3 14h18M5 10V6a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v4m0-3h5a3 3 0 0 1 3 3"/><path d="M3 18v2m18-2v2"/>',
  key: '<circle cx="8" cy="15" r="5"/><path d="m10.8 11.2 8.7-8.7 2 2-2 2 2 2-3 3-2-2-2 2"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  arrow: '<path d="M5 12h14m-7-7 7 7-7 7"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5m5 5H9"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/>',
  arrowUpRight: '<path d="M7 17 17 7M7 7h10v10"/>',
}[name] || '');
const ico = (name, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon(name)}</svg>`;

function toast(message, kind = 'success') {
  const region = document.querySelector('#toast-region');
  const node = document.createElement('div');
  node.className = `toast ${kind}`;
  node.textContent = message;
  region.append(node);
  window.setTimeout(() => node.remove(), 4200);
}

function shell(content) {
  const isStaff = Boolean(state.staff);
  const name = isStaff ? state.staff.role : state.user?.username;
  return `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#" data-action="home"><span class="brand-mark">H</span><span>hotel<span class="brand-light">OS</span></span></a>
      <div class="workspace-label">WORKSPACE</div>
      <nav class="nav-list" aria-label="Main navigation">
        <button class="nav-item ${state.view === 'welcome' ? 'active' : ''}" data-action="home">${ico('grid')}<span>Overview</span></button>
        ${!isStaff || state.staff.role === 'Admin' ? `<button class="nav-item ${state.view === 'bookings' ? 'active' : ''}" data-action="bookings">${ico('calendar')}<span>${isStaff ? 'Reservations' : 'My stays'}</span></button>` : ''}
        ${isStaff && state.staff.role === 'Admin' ? `<button class="nav-item ${state.view === 'rooms' ? 'active' : ''}" data-action="rooms">${ico('bed')}<span>Room inventory</span></button>` : ''}
      </nav>
      <div class="sidebar-bottom"><div class="help-card"><span class="help-dot"></span><strong>HotelOS support</strong><small>Operations, made simple.</small></div><div class="sidebar-footer">© 2026 HotelOS <span>•</span> v1.0</div></div>
    </aside>
    <main class="main-area">
      <header class="topbar"><div class="breadcrumb">HotelOS <span>/</span> <strong>${state.view === 'rooms' ? 'Room inventory' : state.view === 'bookings' ? (isStaff ? 'Reservations' : 'My stays') : 'Overview'}</strong></div>
        <div class="top-actions">${state.apiState === 'online' ? '<span class="connection"><i></i> API connected</span>' : state.apiState === 'offline' ? '<span class="connection offline"><i></i> API offline</span>' : '<span class="connection"><i></i> Connecting</span>'}
        ${name ? `<span class="user-chip"><span class="avatar">${h(name.slice(0, 1).toUpperCase())}</span><span>${h(name)}</span></span><button class="icon-button" aria-label="Sign out" title="Sign out" data-action="logout">${ico('logout')}</button>` : '<button class="button button-small button-outline" data-action="open-auth">Sign in</button>'}</div>
      </header>
      <div class="page-content">${content}</div>
    </main>
  </div>`;
}

function welcomePage() {
  if (state.user) return customerHome();
  if (state.staff) return staffHome();
  return `<section class="welcome-grid">
    <div class="welcome-copy"><div class="eyebrow"><span class="eyebrow-dot"></span> HOTEL OPERATIONS, REIMAGINED</div>
      <h1>Every stay,<br /><span>thoughtfully</span> managed.</h1>
      <p class="lead">A calmer way to manage bookings, guests, and the details that make a stay feel effortless.</p>
      <div class="welcome-actions"><button class="button button-primary" data-action="open-auth">Get started ${ico('arrow')}</button><button class="button button-text" data-action="staff-panel">Staff access</button></div>
      <div class="trust-row"><div class="avatar-stack"><i>H</i><i>O</i><i>S</i></div><span>One clear view for every stay</span></div>
    </div>
    <div class="hero-visual"><div class="hero-image"><div class="image-shade"></div><div class="floating-note"><span class="note-icon">✦</span><span><strong>Thoughtful by design</strong><small>Details in their right place</small></span><span class="note-arrow">↗</span></div><div class="hero-caption"><span>01 — THE GUEST EXPERIENCE</span><strong>Good stays start<br />with a little clarity.</strong></div></div><div class="hero-stat"><span>01</span><div><strong>Stay in sync</strong><small>From booking to check-out</small></div>${ico('arrowUpRight')}</div></div>
  </section>
  <section class="feature-strip"><div><span class="feature-number">01</span><strong>One thoughtful flow</strong><small>From quote to confirmed stay</small></div><div><span class="feature-number">02</span><strong>Clear at a glance</strong><small>Rooms, guests, and reservations</small></div><div><span class="feature-number">03</span><strong>Ready for the day</strong><small>Check-in and check-out, made easy</small></div></section>
  ${state.staffError ? `<div class="inline-alert error">${h(state.staffError)}</div>` : ''}
  <section id="staff-login" class="staff-access ${state.staffPanel ? 'expanded' : ''}"><div><span class="eyebrow">FOR THE TEAM</span><h2>Staff access</h2><p>Sign in to manage room inventory and guest stays.</p></div>${state.staffPanel ? staffLoginForm() : `<button class="button button-outline" data-action="staff-panel">Staff sign in ${ico('arrow')}</button>`}</section>`;
}

function staffLoginForm() {
  return `<form id="staff-login-form" class="staff-form"><label>Role<select name="role"><option value="Admin">Administrator</option><option value="Service">Service staff</option></select></label><label>Password<input type="password" name="password" required autocomplete="current-password" placeholder="Staff password" /></label><button class="button button-dark" type="submit">Sign in ${ico('arrow')}</button></form>`;
}

function authDialog() {
  if (!state.authOpen) return '';
  return `<div class="modal-backdrop" data-action="close-auth"><section class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title"><button class="modal-close" aria-label="Close" data-action="close-auth">×</button><div class="modal-mark">H</div><span class="eyebrow">YOUR HOTEL, IN GOOD HANDS</span><h2 id="auth-title">${state.authMode === 'login' ? 'Welcome back' : 'Create your account'}</h2><p>${state.authMode === 'login' ? 'Sign in to see your stays and plan your next visit.' : 'A few details and you’re ready to book.'}</p>
      ${state.authError ? `<div class="inline-alert error">${h(state.authError)}</div>` : ''}
      <form id="auth-form" class="form-stack"><label>Username<input name="username" autocomplete="username" required minlength="2" maxlength="8" placeholder="2–8 characters" value="${h(state.authUsername || '')}" /></label><label>Password<input name="password" type="password" autocomplete="${state.authMode === 'login' ? 'current-password' : 'new-password'}" required minlength="2" placeholder="At least 2 characters" /></label><button class="button button-primary full-width" type="submit">${state.authMode === 'login' ? 'Sign in' : 'Create account'} ${ico('arrow')}</button></form>
      <div class="auth-switch">${state.authMode === 'login' ? 'New to HotelOS?' : 'Already have an account?'} <button class="link-button" data-action="toggle-auth">${state.authMode === 'login' ? 'Create an account' : 'Sign in'}</button></div>
    </section></div>`;
}

function customerHome() {
  return `<section class="page-heading"><div><div class="eyebrow">YOUR GUEST SPACE</div><h1>Good to see you, ${h(state.user.username)}.</h1><p>Plan a stay or keep track of the details you already have.</p></div><span class="user-id">Guest ID <strong>${h(state.user.user_id)}</strong></span></section>
    <section class="guest-layout"><div class="panel booking-panel"><div class="panel-heading"><div><span class="eyebrow">PLAN YOUR STAY</span><h2>Find your next stay</h2><p>Get a live itemized quote from the hotel’s pricing rules.</p></div><span class="panel-icon">${ico('calendar')}</span></div>
      <form id="quote-form" class="quote-form"><label>Room category<select name="room_type" required><option value="Standard">Standard</option><option value="Deluxe">Deluxe</option><option value="Suite">Suite</option></select></label><div class="date-fields"><label>Arrival<input type="date" name="check_in" value="${state.quote?.check_in || ''}" required /></label><label>Departure<input type="date" name="check_out" value="${state.quote?.check_out || ''}" required /></label></div><button class="button button-primary" type="submit">Calculate my quote ${ico('arrow')}</button></form>
      ${state.quoteError ? `<div class="inline-alert error">${h(state.quoteError)}</div>` : ''}${state.quote ? quoteCard() : ''}
      ${state.quote ? `<form id="booking-form" class="booking-create"><div class="booking-divider"></div><div class="booking-create-heading"><div><span class="eyebrow">READY WHEN YOU ARE</span><h3>Request this room</h3></div><small>Room availability is confirmed by the booking service.</small></div>${state.bookingError ? `<div class="inline-alert error">${h(state.bookingError)}</div>` : ''}${state.bookingSuccess ? `<div class="inline-alert success">${h(state.bookingSuccess)}</div>` : ''}<div class="room-input-row"><label>Room ID<input type="number" name="room_id" min="1" required placeholder="Enter your assigned room ID" /></label><div class="input-hint">Ask the front desk which room ID to book. The API does not expose customer room search.</div><button type="submit" class="button button-dark">Create pre-booking ${ico('arrow')}</button></div></form>` : ''}
    </div><aside class="guest-aside"><div class="aside-art"><div class="art-sun"></div><div class="art-horizon"></div><span>MAKE ROOM<br />FOR A GOOD STAY</span></div><div class="aside-card"><span class="eyebrow">PRICING, WITH CLARITY</span><h3>Know what to expect.</h3><p>Your quote includes nightly rates, demand adjustment, weekend surcharges, and 12% GST.</p><div class="rate-row"><span>Standard</span><strong>₹2,500 <small>/ night</small></strong></div><div class="rate-row"><span>Deluxe</span><strong>₹4,000 <small>/ night</small></strong></div><div class="rate-row"><span>Suite</span><strong>₹6,500 <small>/ night</small></strong></div></div></aside></section>`;
}

function quoteCard() {
  const q = state.quote;
  return `<div class="quote-result"><div class="quote-result-head"><div><span class="eyebrow">YOUR STAY ESTIMATE</span><strong>${h(q.room_type)} <span>·</span> ${q.nights} ${q.nights === 1 ? 'night' : 'nights'}</strong></div><div class="quote-total"><small>Estimated total</small><strong>${money(q.total_price)}</strong></div></div><div class="quote-dates">${ico('calendar')} ${dateLabel(q.check_in)} — ${dateLabel(q.check_out)}</div><div class="quote-lines"><div><span>Base rate × ${q.nights} nights</span><strong>${money(q.base_amount)}</strong></div><div><span>Occupancy adjustment (${q.occupancy_multiplier}×)</span><strong>${money(q.amount_after_occupancy - q.base_amount)}</strong></div><div><span>Weekend surcharge</span><strong>${money(q.weekend_surcharge_total)}</strong></div><div><span>GST (${q.gst_rate_percent}%)</span><strong>${money(q.gst_amount)}</strong></div></div><div class="quote-foot">Projected occupancy for these dates: <strong>${q.projected_occupancy_percent}%</strong></div></div>`;
}

function staffHome() {
  if (state.staff.role === 'Service') return `<section class="page-heading"><div><div class="eyebrow">STAFF WORKSPACE · SERVICE</div><h1>Guest stay actions</h1><p>Use the reservation details provided by the front desk to check a guest in or out.</p></div></section>
    <section class="panel action-panel"><div class="panel-heading"><div><span class="eyebrow">CHECK-IN & CHECK-OUT</span><h2>Update a guest’s stay</h2><p>The API verifies the reservation, guest, dates, and room status before making a change.</p></div><span class="panel-icon">${ico('key')}</span></div>
      ${state.staffError ? `<div class="inline-alert error">${h(state.staffError)}</div>` : ''}${state.serviceSuccess ? `<div class="inline-alert success">${h(state.serviceSuccess)}</div>` : ''}<form id="service-action-form" class="service-action-form"><label>Reservation ID<input name="reservation_id" required placeholder="Reservation ID" /></label><label>Guest ID<input name="user_id" required minlength="1" maxlength="32" placeholder="Guest ID" /></label><label>Action<select name="action"><option value="check-in">Check in</option><option value="check-out">Check out</option></select></label><button class="button button-primary" type="submit">Apply stay action ${ico('arrow')}</button></form><div class="action-note"><span>i</span> Check-in is available only during the booked stay dates, with a clean and empty room. Check-out places the room into housekeeping.</div></section>`;
  const total = state.bookings.filter((b) => b.status !== 'checked_out').length;
  const occupied = state.rooms.flatMap((g) => g.room || []).filter((r) => r.status === 'occupied').length;
  const needsClean = state.rooms.flatMap((g) => g.room || []).filter((r) => r.status === 'cleaning' || r.clean === false).length;
  return `<section class="page-heading"><div><div class="eyebrow">STAFF WORKSPACE · ${h(state.staff.role.toUpperCase())}</div><h1>Here’s the day at a glance.</h1><p>Keep arrivals, departures, and room readiness moving together.</p></div><button class="button button-primary" data-action="bookings">View reservations ${ico('arrow')}</button></section>
    ${state.staffError ? `<div class="inline-alert error">${h(state.staffError)}</div>` : ''}
    <section class="stats-grid"><article class="stat-card"><div class="stat-head">ACTIVE RESERVATIONS <span>${ico('calendar')}</span></div><strong>${state.bookingsState === 'loading' ? '—' : total}</strong><small>Current booking records</small><div class="stat-underline blue"></div></article><article class="stat-card"><div class="stat-head">ROOMS OCCUPIED <span>${ico('key')}</span></div><strong>${state.roomsState === 'loading' ? '—' : occupied}</strong><small>Rooms currently checked in</small><div class="stat-underline green"></div></article><article class="stat-card"><div class="stat-head">HOUSEKEEPING <span>${ico('bed')}</span></div><strong>${state.roomsState === 'loading' ? '—' : needsClean}</strong><small>Rooms awaiting cleaning</small><div class="stat-underline gold"></div></article></section>
    <section class="panel staff-lower"><div class="panel-heading"><div><span class="eyebrow">QUICK ACCESS</span><h2>Keep the essentials close.</h2><p>Pick up where your guests need you.</p></div></div><div class="quick-grid"><button class="quick-link" data-action="bookings"><span class="quick-icon">${ico('calendar')}</span><span><strong>Manage reservations</strong><small>Check guests in and out</small></span>${ico('arrow')}</button><button class="quick-link" data-action="rooms"><span class="quick-icon lavender">${ico('bed')}</span><span><strong>Room inventory</strong><small>Review room readiness</small></span>${ico('arrow')}</button></div>${state.bookingsState === 'error' ? `<div class="inline-alert error">${h(state.bookingsError || 'Could not load reservations.')}</div>` : ''}${state.roomsState === 'error' ? `<div class="inline-alert info">${h(state.roomsError || 'Room inventory is available to administrator accounts.')}</div>` : ''}</section>`;
}

function statusPill(status) {
  const css = String(status || 'unknown').toLowerCase().replace(/[^a-z]+/g, '-');
  return `<span class="status-pill ${h(css)}"><i></i>${h(status || 'Unknown')}</span>`;
}

function loadingBlock(message = 'Loading records…') { return `<div class="state-block"><span class="spinner"></span><strong>${h(message)}</strong></div>`; }
function emptyBlock(title, desc) { return `<div class="state-block empty-state"><span class="empty-mark">✳</span><strong>${h(title)}</strong><p>${h(desc)}</p></div>`; }

function bookingsPage() {
  if (!state.staff) {
    return `<section class="page-heading"><div><div class="eyebrow">YOUR BOOKINGS</div><h1>Your stays, all in one place.</h1><p>Review booking details for guest ID ${h(state.user?.user_id || '')}.</p></div><button class="button button-outline" data-action="home">Plan a stay</button></section>
      <section class="panel data-panel">${state.myBookingsState === 'loading' ? loadingBlock('Finding your stays…') : state.myBookingsState === 'error' ? `<div class="inline-alert error">${h(state.myBookingsError)}</div><button class="button button-outline" data-action="refresh-my-bookings">Try again</button>` : state.myBookings.length ? bookingsTable(state.myBookings, false) : emptyBlock('No stays on the books yet', 'When you create a pre-booking, it will show here.')}</section>`;
  }
  return `<section class="page-heading"><div><div class="eyebrow">FRONT DESK</div><h1>Reservations</h1><p>Review the guest list and move each stay through its lifecycle.</p></div><button class="button button-outline" data-action="refresh-bookings">↻ Refresh</button></section>
    <section class="panel data-panel"><div class="filter-row"><label>Status<select id="filter-status"><option value="">All statuses</option><option value="prebooked">Prebooked</option><option value="checked_in">Checked in</option><option value="checked_out">Checked out</option></select></label><label>Room ID<input id="filter-room" type="number" min="1" placeholder="Any room" /></label><button class="button button-dark" data-action="apply-filter">Apply filters</button></div>
      ${state.bookingsState === 'loading' ? loadingBlock('Loading reservations…') : state.bookingsState === 'error' ? `<div class="inline-alert error">${h(state.bookingsError)}</div><button class="button button-outline" data-action="refresh-bookings">Try again</button>` : state.bookings.length ? bookingsTable(state.bookings, true) : emptyBlock('No reservations found', 'Try a different filter or refresh the list.')}</section>`;
}

function bookingsTable(rows, actions) {
  return `<div class="table-wrap"><table><thead><tr><th>GUEST / RESERVATION</th><th>ROOM</th><th>STAY DATES</th><th>AMOUNT</th><th>STATUS</th>${actions ? '<th>ACTION</th>' : ''}</tr></thead><tbody>${rows.map((b) => {
    const id = b.reservation_id ?? b.id ?? '—';
    const guest = state.staff ? b.user_id : state.user?.username;
    const checkinEnabled = actions && ['prebooked', 'Confirmed', 'Paid'].includes(b.status);
    const checkoutEnabled = actions && b.status === 'checked_in';
    return `<tr><td><strong>${h(guest ?? 'Guest')}</strong><small class="cell-sub">${h(String(id))}</small></td><td><span class="room-label">${h(b.room_type || 'Room')} <small>#${h(b.room_id ?? '—')}</small></span></td><td>${dateLabel(b.check_in)}<small class="cell-sub">to ${dateLabel(b.check_out)}</small></td><td><strong>${b.total_price == null ? '—' : money(b.total_price)}</strong></td><td>${statusPill(b.status || b.reservation_status)}</td>${actions ? `<td><div class="row-actions">${checkinEnabled ? `<button class="table-action" data-action="stay-action" data-stay="check-in" data-id="${h(id)}" data-user="${h(b.user_id)}">Check in</button>` : ''}${checkoutEnabled ? `<button class="table-action" data-action="stay-action" data-stay="check-out" data-id="${h(id)}" data-user="${h(b.user_id)}">Check out</button>` : ''}${!checkinEnabled && !checkoutEnabled ? '<span class="muted">—</span>' : ''}</div></td>` : ''}</tr>`;
  }).join('')}</tbody></table></div>`;
}

function roomsPage() {
  if (state.roomsState === 'loading') return `<section class="page-heading"><div><div class="eyebrow">HOUSEKEEPING & FRONT DESK</div><h1>Room inventory</h1><p>Availability and cleaning status from the live room inventory.</p></div></section><div class="panel data-panel">${loadingBlock('Loading room inventory…')}</div>`;
  if (state.roomsState === 'error') return `<section class="page-heading"><div><div class="eyebrow">HOUSEKEEPING & FRONT DESK</div><h1>Room inventory</h1><p>Availability and cleaning status from the live room inventory.</p></div></section><div class="panel data-panel"><div class="inline-alert error">${h(state.roomsError)}</div><button class="button button-outline" data-action="refresh-rooms">Try again</button></div>`;
  const groups = state.roomFilter === 'all' ? state.rooms : state.rooms.filter((g) => g.type.toLowerCase() === state.roomFilter);
  const allRooms = groups.flatMap((g) => (g.room || []).map((r) => ({ ...r, type: g.type })));
  const tally = (status) => state.rooms.flatMap((g) => g.room || []).filter((r) => status === 'cleaning' ? (r.status === 'cleaning' || r.clean === false) : r.status === status).length;
  return `<section class="page-heading"><div><div class="eyebrow">HOUSEKEEPING & FRONT DESK</div><h1>Room inventory</h1><p>Availability and cleaning status from the live room inventory.</p></div><button class="button button-outline" data-action="refresh-rooms">↻ Refresh</button></section>
    <section class="room-summary"><div><span class="room-summary-icon">${ico('bed')}</span><span><small>TOTAL ROOMS</small><strong>${state.rooms.flatMap((g) => g.room || []).length}</strong></span></div><div><span class="summary-dot available"></span><span><small>READY</small><strong>${tally('empty')}</strong></span></div><div><span class="summary-dot occupied"></span><span><small>OCCUPIED</small><strong>${tally('occupied')}</strong></span></div><div><span class="summary-dot cleaning"></span><span><small>NEEDS CLEANING</small><strong>${tally('cleaning')}</strong></span></div></section>
    <section class="panel data-panel"><div class="room-toolbar"><div><span class="eyebrow">INVENTORY LIST</span><h2>Every room, accounted for.</h2></div><div class="filter-tabs"><button class="${state.roomFilter === 'all' ? 'selected' : ''}" data-room-filter="all">All rooms</button><button class="${state.roomFilter === 'standard' ? 'selected' : ''}" data-room-filter="standard">Standard</button><button class="${state.roomFilter === 'deluxe' ? 'selected' : ''}" data-room-filter="deluxe">Deluxe</button><button class="${state.roomFilter === 'suite' ? 'selected' : ''}" data-room-filter="suite">Suite</button></div></div>
      <div class="room-grid">${allRooms.length ? allRooms.map((room) => `<article class="room-card"><div class="room-card-top"><span>${h(room.type)}</span><small>ROOM</small></div><div class="room-num">${h(room.room_id)}</div><div class="room-card-bottom">${statusPill(room.status)}<span class="cleanliness ${room.clean ? 'is-clean' : 'is-dirty'}"><i></i>${room.clean ? 'Clean' : 'Cleaning required'}</span></div></article>`).join('') : emptyBlock('No rooms in this category', 'Choose another category.')}</div>
    </section>`;
}

function render() {
  let page = state.view === 'bookings' ? bookingsPage() : state.view === 'rooms' && state.staff ? roomsPage() : welcomePage();
  app.innerHTML = shell(page) + authDialog();
  if (state.view === 'bookings' && !state.staff) {
    const status = document.querySelector('#filter-status'); if (status) status.value = state.statusFilter;
  }
}

async function refreshMyBookings() {
  if (!state.user) return;
  state.myBookingsState = 'loading'; state.myBookingsError = ''; render();
  try { state.myBookings = await api.myBookings(state.user.user_id); state.myBookingsState = 'loaded'; }
  catch (error) {
    if (error.message === 'no bookings for this user') { state.myBookings = []; state.myBookingsState = 'loaded'; }
    else { state.myBookings = []; state.myBookingsState = 'error'; state.myBookingsError = error.message; }
  }
  render();
}
async function refreshBookings() {
  if (!state.staff) return;
  state.bookingsState = 'loading'; state.bookingsError = ''; render();
  try { state.bookings = await api.allBookings(state.staff.apiRole, { status: state.statusFilter, room_id: state.roomIdFilter }); state.bookingsState = 'loaded'; }
  catch (error) { state.bookings = []; state.bookingsState = 'error'; state.bookingsError = error.message; }
  render();
}
async function refreshRooms() {
  if (!state.staff) return;
  state.roomsState = 'loading'; state.roomsError = ''; render();
  try { state.rooms = await api.rooms(state.staff.role, state.staffPassword); state.roomsState = 'loaded'; }
  catch (error) { state.rooms = []; state.roomsState = 'error'; state.roomsError = error.message; }
  render();
}

document.addEventListener('click', async (event) => {
  const filter = event.target.closest('[data-room-filter]');
  if (filter) { state.roomFilter = filter.dataset.roomFilter; render(); return; }
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'home') { state.view = 'welcome'; state.staffPanel = false; render(); }
  if (action === 'open-auth') { state.authOpen = true; state.authError = ''; render(); }
  if (action === 'close-auth' && (event.target === button || button.classList.contains('modal-close'))) { state.authOpen = false; render(); }
  if (action === 'toggle-auth') { state.authMode = state.authMode === 'login' ? 'register' : 'login'; state.authError = ''; render(); }
  if (action === 'staff-panel') { state.staffPanel = true; render(); document.querySelector('#staff-login')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  if (action === 'logout') { state.user = null; state.staff = null; state.staffPassword = ''; state.view = 'welcome'; state.quote = null; state.authOpen = false; render(); }
  if (action === 'bookings') { state.view = 'bookings'; render(); state.staff ? refreshBookings() : refreshMyBookings(); }
  if (action === 'rooms') { state.view = 'rooms'; render(); refreshRooms(); }
  if (action === 'refresh-my-bookings') refreshMyBookings();
  if (action === 'refresh-bookings') refreshBookings();
  if (action === 'refresh-rooms') refreshRooms();
  if (action === 'apply-filter') {
    state.statusFilter = document.querySelector('#filter-status')?.value || '';
    state.roomIdFilter = document.querySelector('#filter-room')?.value || '';
    refreshBookings();
  }
  if (action === 'stay-action') {
    const verb = button.dataset.stay;
    button.disabled = true;
    try {
      const result = await api.stayAction(button.dataset.id, verb, button.dataset.user, state.staff.apiRole);
      toast(result.message || `${verb === 'check-in' ? 'Check-in' : 'Check-out'} complete.`);
      await Promise.all([refreshBookings(), state.staff.role === 'Admin' ? refreshRooms() : Promise.resolve()]);
    } catch (error) { toast(error.message, 'error'); button.disabled = false; }
  }
});

document.addEventListener('submit', async (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();
  if (form.id === 'auth-form') {
    const data = Object.fromEntries(new FormData(form));
    state.authError = '';
    if (data.username.trim().length < 2 || data.username.trim().length > 8) { state.authError = 'Username must be 2 to 8 characters.'; render(); return; }
    if (data.password.length < 2) { state.authError = 'Password must be at least 2 characters.'; render(); return; }
    try {
      if (state.authMode === 'register') {
        const result = await api.register({ username: data.username.trim(), password: data.password });
        state.user = { username: result.username, user_id: result.id };
        toast('Your account is ready.');
      } else {
        const result = await api.login({ username: data.username.trim(), password: data.password });
        state.user = { username: result.username, user_id: result.user_id };
        toast('Welcome back.');
      }
      state.authOpen = false; state.view = 'welcome'; state.quote = null; state.bookingError = ''; render();
    } catch (error) { state.authError = error.message; render(); }
  }
  if (form.id === 'staff-login-form') {
    const data = Object.fromEntries(new FormData(form));
    state.staffError = '';
    try {
      await api.staffLogin(data.role, data.password);
      state.staff = { role: data.role, apiRole: data.role.toLowerCase() };
      state.staffPassword = data.password; state.view = 'welcome'; state.staffPanel = false;
      render(); toast(`Signed in as ${data.role.toLowerCase()} staff.`);
      if (data.role === 'Admin') await Promise.all([refreshBookings(), refreshRooms()]);
    } catch (error) { state.staffError = error.message; render(); }
  }
  if (form.id === 'service-action-form') {
    const data = Object.fromEntries(new FormData(form));
    state.staffError = '';
    const submit = form.querySelector('button[type="submit"]'); submit.disabled = true;
    try {
      const result = await api.stayAction(data.reservation_id.trim(), data.action, data.user_id.trim(), state.staff.apiRole);
      toast(result.message || 'Stay updated.');
      state.serviceSuccess = result.message || 'Stay updated.';
    } catch (error) { state.staffError = error.message; }
    render();
  }
  if (form.id === 'quote-form') {
    const data = Object.fromEntries(new FormData(form));
    const invalid = validateStay(data.check_in, data.check_out);
    if (invalid) { state.quoteError = invalid; render(); return; }
    state.quoteError = ''; state.quote = null; render();
    try { state.quote = await api.quote(data); state.bookingSuccess = ''; }
    catch (error) { state.quoteError = error.message; }
    render();
  }
  if (form.id === 'booking-form') {
    const roomId = Number(new FormData(form).get('room_id'));
    if (!Number.isInteger(roomId) || roomId < 1) { state.bookingError = 'Enter a valid room ID.'; render(); return; }
    const payload = { user_id: String(state.user.user_id), room_id: roomId, check_in: state.quote.check_in, check_out: state.quote.check_out };
    state.bookingError = ''; state.bookingSuccess = '';
    const submit = form.querySelector('button[type="submit"]'); submit.disabled = true; submit.innerHTML = '<span class="spinner tiny"></span> Creating…';
    try {
      const result = await api.createBooking(payload);
      state.bookingSuccess = `Pre-booking created. Reservation ${result.reservation_id} · ${money(result.total_price)}.`;
      toast('Your pre-booking was created.');
    } catch (error) { state.bookingError = error.message; }
    render();
  }
});

api.health().then(() => { state.apiState = 'online'; render(); }).catch(() => { state.apiState = 'offline'; render(); });
render();
