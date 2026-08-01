# Supabase Setup (Free Persistence)

This app can store runtime state in Supabase instead of ephemeral local files.

## What This Stores

- Orders
- Stock
- Newsletter emails
- Email queue

Email confirmation logic is unchanged. This only changes where data is saved.

## 1) Create Table in Supabase SQL Editor

Run this SQL:

```sql
create table if not exists public.app_state (
  state_key text primary key,
  state_value jsonb not null,
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_app_state_updated_at on public.app_state;
create trigger trg_app_state_updated_at
before update on public.app_state
for each row execute function public.set_updated_at();
```

## 2) Add Render Environment Variables

Set these on your web service:

- `SUPABASE_URL` = your project URL (example: `https://xyzcompany.supabase.co`)
- `SUPABASE_SERVICE_ROLE_KEY` = service role key from Supabase
- Optional: `SUPABASE_STATE_TABLE=app_state`

## 3) Deploy

After env vars are saved, redeploy. The app will start using Supabase automatically.

## 4) Verify

- Place a test order
- Check admin orders
- Update stock, refresh/reopen admin page
- Values should persist across restarts
