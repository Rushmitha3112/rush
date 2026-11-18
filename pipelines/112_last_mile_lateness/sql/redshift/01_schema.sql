-- Redshift version of sql/postgres/01_schema.sql. Same columns.
-- Facts are distributed on route_id (the join key between the two facts)
-- and sorted on date_key since nearly every query filters a date range.
create schema if not exists lastmile;
create schema if not exists ops;

create table if not exists lastmile.dim_date (
    date_key int primary key, full_date date not null, day_of_week smallint, iso_week smallint,
    month smallint, is_weekend boolean
) diststyle all;

create table if not exists lastmile.dim_station (
    station_key int identity(1,1) primary key, station_code varchar(16) not null, metro varchar(32)
) diststyle all;

create table if not exists lastmile.dim_zone (
    zone_key int identity(1,1) primary key, station_key int not null, zone_id varchar(32) not null
) diststyle all;

create table if not exists lastmile.fact_route (
    route_id varchar(64) primary key, date_key int not null, station_key int not null,
    departure_utc timestamp not null, route_score varchar(16), capacity_cm3 float8, load_cm3 float8,
    n_stops int, n_packages int, n_with_window int, n_late int, n_not_delivered int,
    planned_route_seconds float8, loaded_at timestamp default getdate()
) distkey (route_id) sortkey (date_key);

create table if not exists lastmile.fact_package_delivery (
    route_id varchar(64) not null, package_id varchar(64) not null, date_key int not null,
    station_key int not null, zone_key int, stop_id varchar(8) not null, stop_seq int not null,
    stop_position_pct float8, scan_status varchar(32), is_delivered boolean, has_window boolean,
    tw_start_utc timestamp, tw_end_utc timestamp, est_arrival_utc timestamp, is_late boolean,
    minutes_late float8, planned_service_s float8, volume_cm3 float8,
    primary key (route_id, package_id, stop_id)
) distkey (route_id) sortkey (date_key);
