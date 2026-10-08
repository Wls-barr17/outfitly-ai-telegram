# Deployment

Build and start with docker compose up --build. Configure .env outside the image. Supabase PostgreSQL and Storage remain managed services; Compose does not launch a local database.

Run exactly one polling bot replica. Configure a strong API_ACCESS_TOKEN for private REST routes. /health is a liveness response; /api/health/ready reports whether Supabase credentials loaded at startup.
