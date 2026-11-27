# HotelOS frontend integration

This package adds a browser interface to the supplied main.py, services.py,
revenue.py and prebook.py. It does not replace those files or your JSON records.

## Install on Windows

1. Stop Uvicorn with Ctrl+C.
2. Extract this ZIP to a temporary folder.
3. Copy `web_app.py` and the whole `frontend` directory into
   `C:\Users\Shreyas\HotelOS`, beside your existing `main.py`.
4. Keep your existing important.env and JSON data in the project root.
   The supplied backend files should retain the names main.py, services.py,
   revenue.py and prebook.py (without upload suffixes such as `(3)`).
5. Open a VS Code terminal in HotelOS and run:

```powershell
.\venv\Scripts\python.exe -m uvicorn web_app:app --reload --port 8001
```

6. Open http://127.0.0.1:8001/ (NOT /docs). Keep the terminal running.
   The API docs remain available at http://127.0.0.1:8001/docs.

If a package is missing, install it into the same environment:

```powershell
.\venv\Scripts\python.exe -m pip install fastapi uvicorn python-dotenv
```

Use the team's existing pinned dependencies when available. This code uses
Pydantic 2-style validation through the supplied services.py. No Node.js,
npm install, separate frontend server, or CORS configuration is needed.
Do not open index.html by double-clicking it: the server must serve the page.

## What is included

- Public food and beverage menu.
- Login using existing guest, Service, or Admin credentials.
- Checked-in reservation selector filtered by authenticated ownership for guests.
- Multiple-item food and beverage orders, notes and calculated display totals.
- Cleaning requests with presence and permission fields.
- Guest request history and status filters.
- Staff service desk with valid start/complete/cancel transitions.
- Admin report for collections, charges, outstanding balances and credits.
- Visible incomplete-report warnings and the full report for diagnosis.
- Logout and responsive layouts.

All API paths are relative to the page's origin: changing the port changes
both the frontend and backend together.

## Login and data

Use your existing guest username/password, or exact staff username `Service`
or `Admin` with its password from important.env. Do not put that file in the
frontend folder or commit it. No accounts or passwords are included in this ZIP.

The new POST /api/ui/login checks credentials through services.authenticate.
The frontend keeps the Basic Authorization value only in JavaScript memory;
it is not stored in localStorage/sessionStorage. Reloading or closing the page
clears the login. Logout clears the in-memory credentials and protected views.
This is a local prototype, not a persistent session system. The existing
HTTPBasic decoder supports ASCII credentials; the login form reports this
limitation explicitly. Use HTTPS and a proper shared authentication/session
system before deployment. Base64 is not encryption.

GET /api/ui/reservations authenticates on the server and returns only permitted
reservation metadata; guests cannot select another guest's stay through it.
The server's services/revenue endpoints remain the authority for authorization.

To place requests, users.json must match the existing password encoding (a/b),
reservations.json must include a reservation owned by that guest with status
checked_in, and the matching room in rooms.json must have status occupied.
Prebooked reservations are not eligible for service requests. Staff should
complete the team's check-in workflow before a guest orders.

For revenue, included reservations require integer room_total_paise,
room_paid_paise and service_paid_paise. Missing values are reported, never
invented. Do not mark payments received just to make a report complete.

## Why web_app.py is separate

web_app.py imports the existing main.app, adds the root page and two small UI
routes, and mounts only frontend/ at /hotel-assets. It inserts that mount ahead
of main.py's /{x_role}/{password} catch-all so assets are served correctly.
Your environment/configuration and data files are not under the static mount.
Switch back to `uvicorn main:app` to run the original app without this UI.

## Backend gaps found in the supplied files

This package connects the working services and revenue flows. It does not
pretend the full booking/payment/check-in lifecycle is already implemented.

- reservations.py is not registered in main.py. It references app, HTTPException
  and clock without defining/importing them appropriately and depends on utils
  modules that were not supplied. Its check-in does not set reservation status
  to checked_in, and its checkout/cleaning conditions are inconsistent.
- prebook.py trusts an X-Role header rather than verified identity. The existing
  endpoints remain accessible, so hiding them in this UI does not secure them.
  Its user ID string/length requirements differ from main.py's integer user IDs.
- The old main.py authentication routes put passwords in URL paths. This UI
  does not use those routes, but importing main.app leaves them in the backend.
- Booking does not create the payment fields needed by revenue.py.
- There is no payment-recording endpoint supplied.
- The password encoding is reversible, and JSON writes across the modules do
  not share a complete transaction mechanism.

Consequently this interface has no account-registration, new booking,
check-in/out, or payment buttons. Those workflows need backend integration
before controls can honestly offer them. Keep the server bound to localhost
for this prototype; audit/fix the above endpoints before public deployment.

## Quick walkthrough

1. Open the home page without logging in; the menu should load.
2. Log in as a guest, open Request a service and select a checked-in reservation.
3. Choose a food quantity, send the request and check it appears pending.
4. Log out and log in as Service. In Requests, Start work, then Mark complete.
5. Log in as Admin and open Revenue. Completed charges should increase;
   collected payments must not increase merely because work was completed.
6. A guest should not see staff action buttons or Revenue. Direct requests to
   protected APIs are still rejected by the server.

If you see no checked-in reservations, check your existing reservation status
and ownership. A 409 when placing an order usually means the room/stay is not
active. A 503 indicates missing/invalid data or configuration. Keep error text
and screenshots free of passwords when sharing them.

## Commit the new interface only

From your project root, create a branch and review the changed files:

```powershell
git switch -c shreyas/hotel-frontend
git add web_app.py frontend README_FRONTEND.md VALIDATION.md
git diff --cached --name-only
git commit -m "Add guest services and staff frontend"
git push -u origin HEAD
```

Copy the documentation files from this package too if using those git add paths.
Only commit the intended source/documentation, then open a pull request to main.
Never add important.env or real guest data.
