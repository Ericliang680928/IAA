-- 商務配對串聯：Supabase 建表與函式（只新增 matching_ 開頭的表與 mm_ 開頭的函式，不動人資/財務的任何資料）
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.matching_docs (
  path text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);
create table if not exists public.matching_admin (
  id int primary key default 1 check (id = 1),
  pw_hash text not null,
  updated_at timestamptz not null default now()
);
create table if not exists public.matching_meta (
  id int primary key default 1 check (id = 1),
  version bigint not null default 0
);
insert into public.matching_meta(id, version) values (1, 0) on conflict do nothing;
create table if not exists public.matching_fail (
  id bigserial primary key,
  at timestamptz not null default now()
);

-- 四張表都開 RLS 且不給任何 policy：網頁只能透過下面的函式存取
alter table public.matching_docs enable row level security;
alter table public.matching_admin enable row level security;
alter table public.matching_meta enable row level security;
alter table public.matching_fail enable row level security;

create or replace function public.matching_bump() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update public.matching_meta set version = version + 1 where id = 1;
  return null;
end $$;
drop trigger if exists matching_docs_bump on public.matching_docs;
create trigger matching_docs_bump after insert or update or delete on public.matching_docs
  for each statement execute function public.matching_bump();

create or replace function public.matching_is_admin(pw text) returns boolean
language plpgsql security definer set search_path = public, extensions as $$
declare h text; fails int;
begin
  if pw is null or pw = '' then return false; end if;
  select pw_hash into h from public.matching_admin where id = 1;
  if h is null then return false; end if;
  select count(*) into fails from public.matching_fail where at > now() - interval '10 minutes';
  if fails >= 20 then return false; end if;
  if crypt(pw, h) = h then return true; end if;
  insert into public.matching_fail default values;
  return false;
end $$;

create or replace function public.mm_admin_status() returns boolean
language sql security definer set search_path = public as $$
  select exists(select 1 from public.matching_admin where id = 1);
$$;

create or replace function public.mm_set_admin(newpw text, oldpw text default null) returns boolean
language plpgsql security definer set search_path = public, extensions as $$
begin
  if newpw is null or length(newpw) < 6 then raise exception 'password too short'; end if;
  if exists(select 1 from public.matching_admin where id = 1) then
    if not public.matching_is_admin(oldpw) then raise exception 'wrong password'; end if;
    update public.matching_admin set pw_hash = crypt(newpw, gen_salt('bf')), updated_at = now() where id = 1;
  else
    insert into public.matching_admin(id, pw_hash) values (1, crypt(newpw, gen_salt('bf')));
  end if;
  return true;
end $$;

create or replace function public.mm_check(pw text) returns boolean
language sql security definer set search_path = public as $$
  select public.matching_is_admin(pw);
$$;

create or replace function public.mm_version() returns bigint
language sql security definer set search_path = public as $$
  select version from public.matching_meta where id = 1;
$$;

create or replace function public.mm_read_all(uid text default null, pw text default null) returns jsonb
language plpgsql security definer set search_path = public as $$
declare adm boolean; res jsonb;
begin
  adm := public.matching_is_admin(pw);
  select coalesce(jsonb_object_agg(path, data), '{}'::jsonb) into res
  from public.matching_docs
  where adm
     or path like 'roster/%' or path like 'rounds/%' or path like 'checkins/%'
     or (uid is not null and uid <> '' and path = 'r2picks/' || uid);
  return jsonb_build_object('v', (select version from public.matching_meta where id = 1), 'docs', res, 'admin', adm);
end $$;

create or replace function public.mm_write(p text, d jsonb, uid text default null, pw text default null) returns boolean
language plpgsql security definer set search_path = public as $$
declare adm boolean; ok boolean := false;
begin
  if p is null or p !~ '^[a-z0-9]+/[A-Za-z0-9_-]+$' then raise exception 'bad path'; end if;
  if length(d::text) > 400000 then raise exception 'too large'; end if;
  adm := public.matching_is_admin(pw);
  if adm then ok := true;
  elsif uid is not null and length(uid) >= 8
        and (p = 'r2picks/' || uid or p = 'checkins/' || uid)
        and uid not like 'manual-%' then ok := true;
  end if;
  if not ok then raise exception 'permission denied'; end if;
  insert into public.matching_docs(path, data, updated_at) values (p, d, now())
  on conflict (path) do update set data = excluded.data, updated_at = now();
  return true;
end $$;

create or replace function public.mm_delete(paths text[], pw text) returns integer
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if not public.matching_is_admin(pw) then raise exception 'permission denied'; end if;
  delete from public.matching_docs where path = any(paths);
  get diagnostics n = row_count;
  return n;
end $$;

-- 只處理本系統自己的函式，不影響 schema 內其他函式的權限
revoke all on function public.matching_bump(), public.matching_is_admin(text) from public, anon, authenticated;
grant execute on function public.mm_admin_status(), public.mm_set_admin(text,text), public.mm_check(text),
  public.mm_version(), public.mm_read_all(text,text), public.mm_write(text,jsonb,text,text), public.mm_delete(text[],text)
  to anon, authenticated;
