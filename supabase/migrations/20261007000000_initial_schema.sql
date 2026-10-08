create extension if not exists pgcrypto;

create table if not exists public.cities (
    id uuid primary key default gen_random_uuid(),
    name text unique not null,
    country text not null default 'Colombia',
    latitude double precision not null,
    longitude double precision not null,
    timezone text not null default 'America/Bogota',
    active boolean not null default true
);

insert into public.cities (name, latitude, longitude) values
('Bogotá',4.7110,-74.0721),('Medellín',6.2442,-75.5812),('Cali',3.4516,-76.5320),
('Barranquilla',10.9639,-74.7964),('Cartagena',10.3910,-75.4794),('Bucaramanga',7.1193,-73.1227),
('Pereira',4.8143,-75.6946),('Manizales',5.0703,-75.5138),('Armenia',4.5339,-75.6811),
('Santa Marta',11.2408,-74.1990),('Cúcuta',7.8891,-72.4967),('Ibagué',4.4389,-75.2322),
('Villavicencio',4.1420,-73.6266),('Neiva',2.9273,-75.2819),('Pasto',1.2136,-77.2811),
('Popayán',2.4448,-76.6147),('Montería',8.7479,-75.8814),('Sincelejo',9.3047,-75.3978),
('Valledupar',10.4631,-73.2532),('Tunja',5.5353,-73.3678)
on conflict (name) do nothing;

create table if not exists public.users (
    telegram_id bigint primary key,
    username text,
    first_name text not null,
    last_name text,
    city text not null default 'Bogotá',
    timezone text not null default 'America/Bogota',
    preferred_style text not null default 'CASUAL',
    daily_recommendation_enabled boolean not null default false,
    daily_recommendation_time time not null default '07:00',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.clothing_items (
    id uuid primary key default gen_random_uuid(),
    user_telegram_id bigint not null references public.users(telegram_id) on delete cascade,
    image_path text not null,
    name text,
    category text not null check (category in ('TOP','BOTTOM','OUTERWEAR','FOOTWEAR','ACCESSORY','DRESS')),
    subcategory text,
    garment_type text not null,
    color text not null,
    secondary_color text,
    pattern text,
    material text,
    style text not null,
    fit text,
    season text,
    formality smallint not null default 2 check (formality between 1 and 5),
    warmth smallint not null check (warmth between 1 and 5),
    water_resistance smallint not null default 0 check (water_resistance between 0 and 5),
    description text,
    confidence real not null default 0.7 check (confidence between 0 and 1),
    is_favorite boolean not null default false,
    is_available boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists clothing_items_user_created_idx on public.clothing_items (user_telegram_id, created_at desc);
create index if not exists clothing_items_user_category_idx on public.clothing_items (user_telegram_id, category);

create table if not exists public.weather_snapshots (
    id uuid primary key default gen_random_uuid(),
    user_telegram_id bigint not null references public.users(telegram_id) on delete cascade,
    temperature real not null,
    feels_like real not null,
    min_temperature real not null,
    max_temperature real not null,
    humidity smallint not null default 0,
    rain_probability smallint not null,
    precipitation real not null,
    wind_speed real not null,
    uv_index real not null default 0,
    weather_code integer not null,
    captured_at timestamptz not null default now()
);

create table if not exists public.outfits (
    id uuid primary key default gen_random_uuid(),
    user_telegram_id bigint not null references public.users(telegram_id) on delete cascade,
    score real not null check (score between 0 and 100),
    explanation text not null,
    weather_snapshot jsonb not null,
    weather_snapshot_id uuid references public.weather_snapshots(id),
    item_ids jsonb not null,
    created_at timestamptz not null default now()
);
create index if not exists outfits_user_created_idx on public.outfits (user_telegram_id, created_at desc);

create table if not exists public.outfit_items (
    outfit_id uuid not null references public.outfits(id) on delete cascade,
    clothing_item_id uuid not null references public.clothing_items(id) on delete cascade,
    primary key (outfit_id, clothing_item_id)
);
create table if not exists public.outfit_history (
    id uuid primary key default gen_random_uuid(),
    user_telegram_id bigint not null references public.users(telegram_id) on delete cascade,
    outfit_id uuid not null references public.outfits(id) on delete cascade,
    recommended_at timestamptz not null default now(),
    was_used boolean,
    rating smallint check (rating between 1 and 5)
);
create table if not exists public.user_preferences (
    user_telegram_id bigint primary key references public.users(telegram_id) on delete cascade,
    style_weights jsonb not null default '{}'::jsonb,
    category_weights jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);
create table if not exists public.feedback (
    id uuid primary key default gen_random_uuid(),
    user_telegram_id bigint not null references public.users(telegram_id) on delete cascade,
    outfit_id uuid not null references public.outfits(id) on delete cascade,
    rating smallint not null check (rating between 1 and 5),
    created_at timestamptz not null default now()
);
create index if not exists feedback_user_created_idx on public.feedback (user_telegram_id, created_at desc);

alter table public.users enable row level security;
alter table public.cities enable row level security;
alter table public.clothing_items enable row level security;
alter table public.weather_snapshots enable row level security;
alter table public.outfits enable row level security;
alter table public.outfit_items enable row level security;
alter table public.outfit_history enable row level security;
alter table public.user_preferences enable row level security;
alter table public.feedback enable row level security;

insert into storage.buckets (id, name, public) values ('clothing-images','clothing-images',false)
on conflict (id) do nothing;
