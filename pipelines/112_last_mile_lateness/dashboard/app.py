"""Ops dashboard. Locally this replaces the QuickSight analysis."""
import os

import pandas as pd
import psycopg
import streamlit as st

DSN = os.getenv("PG_DSN", "postgresql://lastmile:lastmile@localhost:5433/lastmile")

st.set_page_config(page_title="Last mile lateness", layout="wide")


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


daily = q("select * from mart.station_daily")
if daily.empty:
    st.warning("Warehouse is empty. Run `make backfill` first.")
    st.stop()

st.title("Last mile lateness")
st.caption("Arrival times are estimated from the driven stop order, travel time matrix and planned service times.")

stations = sorted(daily["station_code"].unique())
pick = st.multiselect("Stations", stations, default=stations)
d = daily[daily["station_code"].isin(pick)]

pk = d["packages"].sum()
windowed = d["windowed_packages"].sum()
late = d["late_packages"].sum() / windowed if windowed else 0
c1, c2, c3, c4 = st.columns(4)
c1.metric("Routes", f"{d['routes'].sum():,}")
c2.metric("Packages", f"{pk:,}")
c3.metric("Late vs window (approx)", f"{late:.1%}")
c4.metric("Avg route length", f"{d['avg_route_hours'].mean():.1f} h")

st.subheader("Late rate by day")
st.line_chart(d.pivot_table(index="full_date", columns="station_code", values="late_rate_windowed"))

left, right = st.columns(2)
with left:
    st.subheader("Zones that run late most often")
    zones = q("select * from mart.zone_lateness order by late_rate desc")
    st.dataframe(zones[zones["station_code"].isin(pick)].head(25), hide_index=True)
with right:
    st.subheader("Van fill vs late rate, per station")
    agg = d.groupby("station_code").agg(van_fill=("avg_van_fill", "mean"), late=("late_rate_windowed", "mean"))
    st.scatter_chart(agg, x="van_fill", y="late")

st.subheader("Pipeline health")
runs = q("select * from ops.latest_runs order by run_date desc")
bad = runs[~runs["status"].isin(["ok", "warn"])]
if bad.empty:
    st.success(f"Last {len(runs)} route dates loaded. Latest: {runs['run_date'].max()}")
else:
    st.error(f"{len(bad)} dates not loaded: {', '.join(map(str, bad['run_date']))}")
st.dataframe(runs.head(15), hide_index=True)
dq = q("""select run_date, check_name, severity, observed, threshold from ops.dq_results
          where not passed order by run_date desc limit 50""")
if not dq.empty:
    st.caption("Failed or warning checks")
    st.dataframe(dq, hide_index=True)
