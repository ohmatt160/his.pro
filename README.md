# HIS.Pro - Health Information System

A comprehensive healthcare information system built with Flask (Python) backend and React frontend.

## Features

- Multi-workspace/tenant architecture for healthcare facilities
- Patient management
- Appointments scheduling
- Electronic Medical Records
- Laboratory orders
- Pharmacy management
- Billing & Invoicing
- Inventory management
- Dashboard with analytics

## Deployment

This project is deployed on Hugging Face Spaces using Docker.

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

The app will be available at http://localhost:5000

### Building Frontend

The frontend is pre-built and static files are in `app/static`. To rebuild:

```bash
cd app/templates/healthsuite-pro copy
npm install
npm run build
# Copy build output to app/static
```

## Tech Stack

- **Backend**: Flask, SQLAlchemy, JWT authentication
- **Frontend**: React, TypeScript, Tailwind CSS, shadcn/ui
- **Database**: SQLite (default) or PostgreSQL (production)
- **Deployment**: Docker, Hugging Face Spaces

## API Endpoints

- `/api/v1/auth` - Authentication
- `/api/v1/patients` - Patient management
- `/api/v1/appointments` - Appointment scheduling
- `/api/v1/dashboard` - Dashboard statistics
- `/api/v1/facilities` - Facility management
- And more...

## License

MIT