create schema if not exists mart;

create or replace view mart.station_daily as
select d.full_date,
       s.station_code,
       count(distinct r.route_id)                                  as routes,
       sum(r.n_packages)                                           as packages,
       sum(r.n_with_window)                                        as windowed_packages,
       sum(r.n_late)                                               as late_packages,
       sum(r.n_late)::numeric / nullif(sum(r.n_with_window), 0)    as late_rate_windowed,
       sum(r.n_not_delivered)::numeric / nullif(sum(r.n_packages), 0) as not_delivered_rate,
       avg(r.planned_route_seconds) / 3600                         as avg_route_hours,
       avg(r.load_cm3 / nullif(r.capacity_cm3, 0))                 as avg_van_fill
from lastmile.fact_route r
join lastmile.dim_date d using (date_key)
join lastmile.dim_station s using (station_key)
group by 1, 2;

-- zones that run late again and again are the hiring / route split candidates
create or replace view mart.zone_lateness as
select s.station_code,
       z.zone_id,
       count(*) filter (where f.has_window)                            as windowed_packages,
       avg(f.is_late::int) filter (where f.has_window)                 as late_rate,
       percentile_cont(0.9) within group (order by f.minutes_late)     as p90_minutes_late_when_late,
       count(distinct f.date_key)                                      as active_days,
       avg(f.stop_position_pct)                                        as avg_position_in_route
from lastmile.fact_package_delivery f
join lastmile.dim_zone z using (zone_key)
join lastmile.dim_station s on s.station_key = f.station_key
group by 1, 2
having count(*) filter (where f.has_window) >= 50;

-- freshness for the dashboard / SLA check: data for day D should be in by 06:00 UTC on D+1
create or replace view ops.latest_runs as
select distinct on (run_date) run_date, status, trigger, started_at, finished_at, routes, packages, error
from ops.pipeline_runs
order by run_date, started_at desc;
