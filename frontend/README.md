# HotelOS frontend

Responsive guest and staff interface for the FastAPI service in the project root. The UI uses the implemented routes for guest registration and login, stay quotes, pre-bookings, booking lookup, administrator room inventory, and staff check-in/check-out.

## Run locally

Start the backend from the project root in one terminal:

```bash
uvicorn main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). Vite proxies `/backend/*` to `http://127.0.0.1:8000`, avoiding a backend CORS change. To use a different backend for development, copy `.env.example` to `.env.local` and set `VITE_BACKEND_URL`.

For a production build, run `npm run build`. When hosting the static `dist/` output separately, configure a reverse proxy from `/backend` to the FastAPI origin, or set `VITE_API_BASE_URL` to the API origin and enable CORS on that deployment.

## Workflows and backend limits

- Guests can create an account, sign in, view their own bookings, get itemized live quotes, and create pre-bookings.
- Customers enter the room ID assigned by the hotel because the backend has no public room search or availability endpoint.
- Administrators can view all bookings, filter by status or room ID, inspect room inventory, and check guests in or out.
- Service staff can use the stay action form for a known reservation and guest ID. The backend does not allow service staff to list all bookings or fetch room inventory.
- Manager actions are accepted by the booking and stay routes, but the backend does not provide manager authentication. The frontend therefore offers the staff login roles actually implemented: Admin and Service.
- The guest booking path and user ID validation come directly from the API. Backend errors, including missing user booking records, are shown in the interface.
