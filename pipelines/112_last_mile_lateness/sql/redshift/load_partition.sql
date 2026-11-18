-- Run by the loader Lambda with the Redshift Data API batch call, which runs
-- all statements in one transaction (so no begin/commit here).
-- {run_date}, {date_key}, {curated}, {iam_role} are filled in by redshift_loader.py.
create temp table stage_pkg_raw (
    route_id varchar(64), stop_id varchar(8), package_id varchar(64), scan_status varchar(32),
    planned_service_time_seconds float8, depth_cm float8, height_cm float8, width_cm float8,
    seq int, zone_id varchar(32), est_arrival_utc timestamp, stop_position_pct float8,
    tw_start timestamp, tw_end timestamp, has_window boolean, is_late boolean, minutes_late float8,
    is_delivered boolean, volume_cm3 float8
);
create temp table stage_route_raw (
    route_id varchar(64), station_code varchar(16), executor_capacity_cm3 float8, route_score varchar(16),
    departure_utc timestamp, n_stops int, planned_route_seconds float8, n_packages int, n_late int,
    n_with_window int, n_not_delivered int, load_cm3 float8
);

copy stage_route_raw from '{curated}/route/route_date={run_date}/' iam_role '{iam_role}' format as parquet;
copy stage_pkg_raw from '{curated}/package_delivery/route_date={run_date}/' iam_role '{iam_role}' format as parquet;

insert into lastmile.dim_date
select {date_key}, '{run_date}'::date, date_part(dow, '{run_date}'::date), date_part(week, '{run_date}'::date),
       date_part(month, '{run_date}'::date), date_part(dow, '{run_date}'::date) in (0, 6)
where not exists (select 1 from lastmile.dim_date where date_key = {date_key});

insert into lastmile.dim_station (station_code)
select distinct station_code from stage_route_raw
where station_code not in (select station_code from lastmile.dim_station);

insert into lastmile.dim_zone (station_key, zone_id)
select distinct s.station_key, p.zone_id
from stage_pkg_raw p join stage_route_raw r using (route_id) join lastmile.dim_station s using (station_code)
where p.zone_id is not null
  and not exists (select 1 from lastmile.dim_zone z where z.station_key = s.station_key and z.zone_id = p.zone_id);

delete from lastmile.fact_package_delivery where date_key = {date_key};
delete from lastmile.fact_route where date_key = {date_key};

insert into lastmile.fact_route
select r.route_id, {date_key}, s.station_key, r.departure_utc, r.route_score, r.executor_capacity_cm3, r.load_cm3,
       r.n_stops, r.n_packages, r.n_with_window, r.n_late, r.n_not_delivered, r.planned_route_seconds, getdate()
from stage_route_raw r join lastmile.dim_station s using (station_code);

insert into lastmile.fact_package_delivery
select p.route_id, p.package_id, {date_key}, f.station_key, z.zone_key, p.stop_id, p.seq, p.stop_position_pct,
       p.scan_status, p.is_delivered, p.has_window, p.tw_start, p.tw_end, p.est_arrival_utc, p.is_late,
       p.minutes_late, p.planned_service_time_seconds, p.volume_cm3
from stage_pkg_raw p
join lastmile.fact_route f on f.route_id = p.route_id
left join lastmile.dim_zone z on z.station_key = f.station_key and z.zone_id = p.zone_id;

