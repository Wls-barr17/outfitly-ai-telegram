# Architecture

    Telegram / REST API
            ↓
    Presentation handlers and FastAPI routes
            ↓
    Application services
            ↓
    Domain models and recommendation rules
            ↓
    Supabase PostgREST / Storage, Gemini, Open-Meteo

Telegram handlers and API routes delegate to WardrobeService, OutfitService and WeatherService. The recommendation engine is deterministic and receives only the user's available garments, preferences, recent outfit item IDs and weather. Supabase is accessed through one integration client; Gemini and Open-Meteo each have their own HTTP client.

Supabase's private Storage bucket contains original user photos. PostgreSQL holds metadata and relationships, never image bytes. All wardrobe reads and mutations filter by user_telegram_id; item API mutations filter by both owner ID and item ID.

## Photo analysis

    Telegram photo → MIME/signature/size validation → Gemini structured JSON
          → Pydantic validation → user confirmation → private Storage → PostgreSQL

The bot displays the validated result and asks for confirmation before the storage and database writes.

## Recommendation flow

    Profile city → Open-Meteo → available wardrobe → weather/color/style rules
          → preference weights + recent outfit penalty → ranked candidates
          → persist weather snapshot and outfit → Telegram / REST

Weights live in RecommendationWeights. Feedback updates bounded per-subcategory preference weights; this is a transparent rule, not a trained model.
