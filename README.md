# Outfitly.AI

**Your wardrobe. Your weather. Your outfit.**

Outfitly.AI is a Telegram personal stylist MVP. It stores a user's wardrobe in private Supabase Storage, classifies uploaded clothing with Gemini, and builds deterministic outfit recommendations from owned items and current Open-Meteo weather.

## Features

- Telegram registration, city selection, style preference and daily delivery toggle.
- Clothing photo analysis with Gemini JSON output, validation and explicit save confirmation.
- Private Supabase Storage and user-scoped wardrobe CRUD.
- Colombian city catalog and Open-Meteo current conditions plus daily forecast.
- Recommendation scoring for weather, color, style, preference and outfit repetition.
- Outfit history, weather snapshots and feedback that adjusts category preference weights.
- FastAPI REST API with bearer token protection for private routes.
- APScheduler sends subscribed recommendations in each user's timezone.

## Stack

Python 3.12+, FastAPI, Pydantic v2, python-telegram-bot, httpx, Supabase PostgreSQL/PostgREST and Storage, Gemini, Open-Meteo, APScheduler, Docker and pytest.

The runtime accesses Supabase PostgreSQL through PostgREST. The schema is managed by the Supabase SQL migration in supabase/migrations. DATABASE_URL and SQLAlchemy/Alembic dependencies are included for the planned direct PostgreSQL adapter but are not required by this MVP.

## Setup

1. Create a Supabase project and private clothing-images bucket (the SQL migration also creates it).
2. Create a Telegram bot with BotFather.
3. Create a Gemini API key.
4. Copy .env.example to .env and set:

    TELEGRAM_BOT_TOKEN=
    GEMINI_API_KEY=
    GEMINI_MODEL=gemini-2.5-flash
    SUPABASE_URL=
    SUPABASE_SERVICE_ROLE_KEY=
    API_ACCESS_TOKEN=

SUPABASE_SERVICE_ROLE_KEY and API_ACCESS_TOKEN are server secrets. Never commit .env or expose either value to a client. Private REST routes return 503 until API_ACCESS_TOKEN is set.

Run supabase/migrations/20261007000000_initial_schema.sql in the Supabase SQL Editor. It creates users, cities, clothing, outfits, feedback, history and weather tables, and enables row-level security. Backend requests use the service role key; application queries include the Telegram user ID for user-owned data.

## Run locally

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    Copy-Item .env.example .env
    python -m uvicorn app.main:app --reload

In a second terminal, start the Telegram bot:

    python -m app.bot.runner

API docs: http://localhost:8000/docs. Health: /health and /api/health.

## Docker

After completing .env and applying the schema:

    docker compose up --build

Compose runs API and Telegram polling bot as separate processes.

## Telegram commands

 /start, /help, /today, /outfit, /add, /clothes, /mycloset, /city, /preferences, /settings, /history, /stats, /delete ID.

The bot has inline buttons for city, style, daily recommendation and feedback. To add a garment, the user confirms the AI analysis before saving. Clothing edits are available through REST API; Telegram editing and closet pagination are future work.

## API

Private endpoints require Authorization: Bearer API_ACCESS_TOKEN; endpoints operating on a user also take telegram_id as a query parameter. Available routes include /api/users/{telegram_id}, /api/clothing, /api/clothing/{id}, /api/outfits/today, /api/outfits/generate, /api/outfits/history, /api/weather/{city}, and /api/preferences.

POST /api/clothing accepts JSON with image_base64, mime_type and confirmed. First send confirmed=false to get a 202 analysis preview; after user approval, send the same image with confirmed=true to persist it. PUT and DELETE scope each mutation by both item ID and Telegram ID.

For direct PostgreSQL schema management, set DATABASE_URL and run alembic upgrade head. Supabase Storage bucket setup still uses the Supabase SQL migration.

## Verification and style

    python -m pytest
    python -m ruff check app tests
    python -m ruff format --check app tests

## Project map

    app/
      bot/handlers/       Telegram presentation
      config/             environment settings
      domain/             validated clothing and weather models
      integrations/       Gemini, Supabase and Open-Meteo clients
      recommendation/     weather, color and scoring rules
      scheduler/          daily delivery
      services/           wardrobe, weather and outfit use cases
      main.py             FastAPI API
    supabase/migrations/  initial Supabase schema
    tests/                unit and API tests
    docs/                 architecture and integration notes

## Current boundaries

- Supabase, Telegram and Gemini need valid external credentials for end-to-end use.
- Private API routes use a shared server bearer token; a public mobile/web client needs Telegram WebApp init-data verification or another user authentication layer.
- The Telegram bot uses polling and one scheduler process. Run one bot replica to avoid duplicate scheduled messages.
- Outfit generation requires at least one available top, bottom and footwear item.
- Database schema application currently uses Supabase SQL Editor and runtime calls use PostgREST. The direct SQLAlchemy/Alembic adapter is planned, not wired into runtime.

## Roadmap

Telegram WebApp authentication, paginated wardrobe browsing, Telegram clothing editing, richer occasion rules, a direct SQLAlchemy/Alembic PostgreSQL adapter, and richer feedback analytics.
