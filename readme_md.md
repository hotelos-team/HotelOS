# FastAPI User & Room Management API

A lightweight backend REST API built with **FastAPI** that handles user registration, authentication, role-based access control (`User`, `Admin`, `Service`), and JSON-based local data storage.

## Features

* **User Authentication**: Sign up and log in with automatic incremental `user_id` generation.
* **Custom Encryption**: Passwords are encrypted and decrypted using a custom linear cipher ($\text{ord}(c) \times a + b$) configured via environment variables.
* **Role-Based Access Control (RBAC)**: Differentiates between `User`, `Admin`, and `Service` roles to restrict sensitive endpoints.
* **Local JSON Storage**: Persists user and room data in local `users.json` and `rooms.json` files without requiring an external database.
* **Interactive API Docs**: Built-in Swagger UI and ReDoc provided automatically by FastAPI.

---

## Prerequisites

* Python 3.8+
* `pip` (Python package manager)

---

## Installation & Setup

1. **Clone or download the project** into your local directory (assuming your main file is named `main.py`).

2. **Install the required dependencies:**
   ```bash
   pip install fastapi uvicorn python-dotenv pydantic
   ```

3. **Create the environment configuration file:**
   Create a file named `important.env` in the root directory of your project and add the following keys:
   ```env
   a=3
   b=7
   Admin_pass=your_secure_admin_password
   Service_pass=your_secure_service_password
   ```
   *(Note: `a` and `b` must be integers used as keys for the password encryption/decryption algorithm).*

4. **Optional - Create `rooms.json`:**
   If you plan to use the `/rooms` endpoint, ensure a `rooms.json` file exists in the root directory (e.g., `[]`). `users.json` will be created automatically upon the first user signup.

---

## Running the Server

Start the FastAPI development server using `uvicorn`:

```bash
uvicorn main:app --reload
```
*(Replace `main` with your actual Python filename if different).*

Once running, the API will be accessible at `http://127.0.0.1:8000`.
* **Swagger UI Documentation:** `http://127.0.0.1:8000/docs`
* **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

---

## API Endpoints

### Server
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Checks if the server is running. Returns `{"status": "ok"}`. | Public |
| `GET` | `/users/{x_role}/{password}` | Retrieves all records from `users.json`. | `Admin` only |
| `GET` | `/rooms/{x_role}/{password}` | Retrieves all records from `rooms.json`. | `Admin` only |

### User
| Method | Endpoint | Query Params | Description | Access |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/signup/{username}/{password}` | `x_role` (default: `User`) | Registers a new user, encrypts their password, and saves to `users.json`. | `User` only |
| `GET` | `/login/{username}/{password}` | `x_role` (default: `User`) | Validates user credentials against `users.json`. | `User` only |

### Staff
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/{x_role}/{password}` | Authenticates `Admin` or `Service` staff using credentials from `important.env`. | `Admin`, `Service` |

---

## Security & Implementation Notes

* **Data Storage**: User credentials are saved in `users.json` in the format:
  ```json
  [
    {
      "user_id": 1,
      "username": "example_user",
      "password": "encrypted_string"
    }
  ]
  ```
* **Production Warning**: This project uses a custom mathematical cipher for learning/demonstration purposes and passes credentials via URL paths. For production environments, consider passing credentials in request bodies (`POST`) over HTTPS and using standard hashing libraries like `passlib` (bcrypt).
