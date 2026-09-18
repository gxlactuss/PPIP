# Placement Prep App - Project Handover

## 1. Tech Stack & Architecture
* **Backend:** FastAPI (Python), PostgreSQL, Google Gemini API
* **Frontend:** Swift / SwiftUI (MVVM architecture)
* **Authentication:** JWT (JSON Web Tokens) with secure password hashing (`passlib`)

## 2. Environment Setup (`.env`)
Create a `.env` file inside the `backend` folder using the `.env.example` template with these variables:
```env
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/placed_db
JWT_SECRET_KEY=<your-secret-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
GEMINI_API_KEY=<your-gemini-api-key>
CORS_ORIGINS=["http://localhost:3000"]

Frontend Integration Details (Swift App)
Base URL: Configured in NetworkManager.swift pointing to http://localhost:8000.

Authentication Flow:

The /api/auth/login endpoint returns a JWT access token upon successful authentication.

Tokens are managed securely using KeychainService.swift.

Protected routes require the Authorization: Bearer <token> header.

Key API Endpoints:

POST /api/auth/register - User registration

POST /api/auth/login - User login & token generation

GET /api/quiz/ - Fetch placement quiz questions

POST /api/interview/start - Initialize an AI-driven interview session