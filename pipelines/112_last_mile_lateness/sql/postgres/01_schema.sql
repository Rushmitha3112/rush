-- Star schema. Postgres locally, sql/redshift/ has the Redshift version
-- (same columns, dist/sort keys instead of indexes).
create schema if not exists lastmile;
create schema if not exists ops;

create table if not exists lastmile.dim_date (
    date_key     int primary key,          -- yyyymmdd
    full_date    date not null unique,
    day_of_week  smallint not null,        -- 1 = Monday
    iso_week     smallint not null,
    month        smallint not null,
    is_weekend   boolean not null
);

create table if not exists lastmile.dim_station (
    station_key   serial primary key,
    station_code  text not null unique,
    metro         text                     -- first letter of code, D=LA area etc. filled when known
);

create table if not exists lastmile.dim_zone (
    zone_key     serial primary key,
    station_key  int not null references lastmile.dim_station,
    zone_id      text not null,
    unique (station_key, zone_id)
);

create table if not exists lastmile.fact_route (
    route_id               text primary key,
    date_key               int not null references lastmile.dim_date,
    station_key            int not null references lastmile.dim_station,
    departure_utc          timestamp not null,
    route_score            text,
    capacity_cm3           double precision,
    load_cm3               double precision,
    n_stops                int,
    n_packages             int,
    n_with_window          int,
    n_late                 int,
    n_not_delivered        int,
    planned_route_seconds  double precision,
    loaded_at              timestamptz not null default now()
);
create index if not exists fact_route_date on lastmile.fact_route (date_key);

create table if not exists lastmile.fact_package_delivery (
    route_id           text not null,
    package_id         text not null,
    date_key           int not null references lastmile.dim_date,
    station_key        int not null references lastmile.dim_station,
    zone_key           int references lastmile.dim_zone,
    stop_id            text not null,
    stop_seq           int not null,
    stop_position_pct  double precision,
    scan_status        text,
    is_delivered       boolean,
    has_window         boolean,
    tw_start_utc       timestamp,
    tw_end_utc         timestamp,
    est_arrival_utc    timestamp,
    is_late            boolean,
    minutes_late       double precision,
    planned_service_s  double precision,
    volume_cm3         double precision,
    -- grain is package x stop: a failed attempt and the later delivery are two rows
    primary key (route_id, package_id, stop_id)
);
create index if not exists fact_pkg_date on lastmile.fact_package_delivery (date_key);
create index if not exists fact_pkg_zone on lastmile.fact_package_delivery (zone_key);

-- one row per attempt, so reruns and backfills are visible
create table if not exists ops.pipeline_runs (
    run_id        bigserial primary key,
    run_date      date not null,
    trigger       text not null,               -- daily | backfill | manual
    status        text not null,               -- running | ok | warn | failed_checks | error
    started_at    timestamptz not null default now(),
    finished_at   timestamptz,
    routes        int,
    packages      int,
    error         text
);
create index if not exists runs_by_date on ops.pipeline_runs (run_date, started_at desc);

create table if not exists ops.dq_results (
    run_id     bigint not null references ops.pipeline_runs,
    run_date   date not null,
    check_name text not null,
    severity   text not null,
    passed     boolean not null,
    observed   double precision,
    threshold  text,
    detail     text
);
