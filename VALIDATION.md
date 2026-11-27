# Validation — 27 November 2026

Tested with copies of the supplied main(3).py, prebook(1).py, services(2).py
and revenue(2).py renamed to their import names in an isolated temporary folder.
Synthetic users, two occupied rooms and two checked-in reservations were used.
No real hotel records or environment file were used or modified.

Passed using FastAPI TestClient:
- Root HTML, JavaScript, stylesheet and API docs return HTTP 200.
- Asset routing works ahead of the legacy dynamic staff route.
- Public menu returns six items.
- Wrong password is rejected; correct guest login returns User role.
- Reservation listing requires authentication and filters guest ownership.
- Guest cannot create a request for another guest's reservation.
- Two sandwiches produce a 24,000-paise request.
- Guest cannot update service status.
- Pending to completed is rejected; staff can do pending -> in_progress -> completed.
- Cleaning request succeeds.
- Another guest cannot see the first guest's requests.
- Guest and Service accounts cannot read revenue.
- Admin report remains complete: collections 600,000 paise; completed services
  24,000 paise; outstanding 1,424,000 paise for the two synthetic reservations.

Also passed Python compilation and `node --check frontend/app.js`.

Limit: a browser test was prepared but could not run because Chromium was not
installed and its download was blocked by the environment. No claim is made
that rendered layout, mobile layout or browser interactions were exercised.
Follow README_FRONTEND.md's walkthrough on your laptop to check those.

This validates the connected service/revenue flows, not the team's incomplete
booking, payment, registration or check-in/check-out workflows.
