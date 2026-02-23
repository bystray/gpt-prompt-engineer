create table if not exists prompts (
  id uuid primary key,
  title text not null,
  content text not null,
  tags text[] default '{}',
  model text not null,
  config jsonb not null,
  examples text[] default '{}',
  created_at timestamptz default now()
);

create table if not exists prompt_versions (
  id bigint generated always as identity primary key,
  prompt_id uuid references prompts(id) on delete cascade,
  version int not null,
  content text not null,
  created_at timestamptz default now(),
  unique (prompt_id, version)
);
