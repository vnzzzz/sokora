# sokora

![image](docs/images/image1.png)

A sleek attendance management app that lets you track who's working where with a calendar interface and intuitive
controls. Instantly see who's "working from home / in office / on business trip" with daily details and personal
schedules available at a glance.

## Features

- Calendar UI
  - Monthly view with aggregated stats for remote/office attendance
- Intuitive UX: Click on dates for daily details, click on usernames to view individual schedules
- CSV Upload & Download
  - Perfect for bulk editing and backups

## How to

1. Launch

   ```bash
   docker compose up --build
   ```

2. Access

   Open in your browser

   ```bash
   http://localhost:8000
   ```

3. Shutdown

   ```bash
   docker compose down
   ```

## Tech Stack

Built with a focus on lightweight simplicity.

- Docker (Containerization)
- Poetry (Dependency management)
- FastAPI (API)
- HTMX & Alpine.js (No-build UI)
- Chart.js (Visual data representation with pie charts and more)
- CSV files (Data source, no database required)
