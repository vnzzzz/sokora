# sokora

![image](docs/images/image1.png)

A sleek attendance management app that visualizes work locations through an intuitive calendar interface. Instantly
track who's "working from home", "in office", or "on business trip" with daily details and personal schedules available
at a glance.

## Features

- Interactive Calendar UI
  - Monthly view with aggregated stats for remote/office attendance
- Intuitive UX: Single-click navigation to view daily details or individual schedules
- Seamless CSV Import/Export
  - Perfect for bulk editing and data backups

## How to Use

1. Setup

   Copy `.env.sample` to create `.env`, then:

   ```bash
   docker compose up --build
   ```

2. Access

   Open in your browser:

   ```bash
   http://localhost:[SERVICE_PORT]
   ```

3. Shutdown

   ```bash
   docker compose down
   ```

## Tech Stack

Built with a focus on performance and simplicity.

- Docker (Containerization)
- Poetry (Python dependency management)
- FastAPI (Backend API)
- HTMX & Alpine.js (Frontend without build steps)
- CSV files (Data source, no database required)
