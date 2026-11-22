
# GSHOP

GSHOP is a web application being developed as part of a larger group of companies.

## Technology Stack

### Backend
- Python 3.13
- Django 5.2
- Django REST Framework
- MySQL 8.0+

### Frontend
- React
- TypeScript
- Vite

## Project Structure

```text
GSHOP/
├── backend/
│   ├── accounts/
│   ├── config/
│   ├── manage.py
│   └── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

Install the following on your computer:

- Python 3.13
- MySQL Server 8.0+
- Node.js 24+
- Git
- Visual Studio Code (recommended)

## Backend Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Create your local environment file by copying `backend/.env.example` to `backend/.env`.
4. Configure your local MySQL credentials in `backend/.env`.

## Database

Create a MySQL database named `gshop` using UTF-8 (`utf8mb4`).

Each developer must configure their own local database credentials. Never commit actual passwords or `.env` files.

## Security

- Never commit `.env` files.
- Never commit `.venv/`.
- Never share database passwords through GitHub.

## Development Status

GSHOP development is in progress.
