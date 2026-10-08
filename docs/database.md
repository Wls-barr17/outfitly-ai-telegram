# Database

Apply supabase/migrations/20261007000000_initial_schema.sql in the Supabase SQL Editor. It creates users, cities, clothing_items, outfits, outfit_items, weather_snapshots, outfit_history, user_preferences and feedback with primary/foreign keys, checks and lookup indexes.

Telegram ID is the users primary key. Clothing records and generated outfits reference it with cascade deletion. The clothing-images bucket is private; object keys are {telegram_id}/{clothing_uuid}/{random_file}.{extension}.

RLS is enabled. The backend uses the Supabase service role key and must never expose it to clients. The application also scopes PostgREST reads/writes by Telegram ID. A public client needs verified Telegram WebApp init data or another authenticated identity before it calls user-scoped endpoints.

The current schema lifecycle is Supabase SQL Editor based; a direct SQLAlchemy/Alembic runtime adapter remains future work.
