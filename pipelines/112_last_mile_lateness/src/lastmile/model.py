"""Which packages are likely to miss their window, using only what is known
when the van leaves the station.

Trained on the warehouse, split by date (train on earlier days, test on the
last 9) so nothing from the future leaks into training. Compared against a
plain baseline: the zone's historical late rate.

Caveat worth saying out loud: the label comes from *estimated* arrival
(see transform.py), and stop_position uses the driven order. In production
you'd use the planned sequence for that feature.
"""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

from .settings import Settings

log = logging.getLogger(__name__)

QUERY = """
select f.date_key, s.station_code, z.zone_id, f.stop_position_pct,
       extract(epoch from (f.tw_end_utc - f.tw_start_utc)) / 3600   as window_hours,
       extract(epoch from (f.tw_end_utc - r.departure_utc)) / 3600  as hours_to_window_end,
       f.planned_service_s, f.volume_cm3,
       r.n_packages as route_packages, r.n_stops as route_stops,
       r.load_cm3 / nullif(r.capacity_cm3, 0) as van_fill,
       extract(hour from r.departure_utc) as departure_hour,
       f.is_late
from lastmile.fact_package_delivery f
join lastmile.fact_route r using (route_id)
join lastmile.dim_station s on s.station_key = f.station_key
left join lastmile.dim_zone z on z.zone_key = f.zone_key
where f.has_window
"""

NUMERIC = ["stop_position_pct", "window_hours", "hours_to_window_end", "planned_service_s", "volume_cm3",
           "route_packages", "route_stops", "van_fill", "departure_hour", "zone_hist_late", "station_hist_late"]


def add_history(train: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Historical late rates from the training days only, smoothed toward the global rate."""
    prior = train["is_late"].mean()
    out = df.copy()
    for key, col, k in [(["station_code", "zone_id"], "zone_hist_late", 50),
                        (["station_code"], "station_hist_late", 200)]:
        g = train.groupby(key)["is_late"].agg(["sum", "count"])
        g[col] = (g["sum"] + k * prior) / (g["count"] + k)
        out = out.merge(g[[col]], left_on=key, right_index=True, how="left")
        out[col] = out[col].fillna(prior)
    return out


def recall_at_precision(y, p, target=0.3):
    prec, rec, _ = precision_recall_curve(y, p)
    ok = rec[prec >= target]
    return float(ok.max()) if len(ok) else 0.0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = Settings.from_env()
    with psycopg.connect(cfg.pg_dsn) as conn:
        df = pd.read_sql(QUERY, conn)
    df["is_late"] = df["is_late"].astype(int)

    days = sorted(df["date_key"].unique())
    cut = days[-9]
    train, test = df[df["date_key"] < cut], df[df["date_key"] >= cut]
    train_h, test_h = add_history(train, train), add_history(train, test)
    log.info("train %d rows / %d days, test %d rows / %d days, late rate %.3f",
             len(train), train["date_key"].nunique(), len(test), test["date_key"].nunique(), df["is_late"].mean())

    model = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                           class_weight="balanced", random_state=7)
    model.fit(train_h[NUMERIC], train_h["is_late"])
    p_model = model.predict_proba(test_h[NUMERIC])[:, 1]
    p_base = test_h["zone_hist_late"].to_numpy()
    y = test_h["is_late"].to_numpy()

    report = {
        "train_days": int(train["date_key"].nunique()), "test_days": int(test["date_key"].nunique()),
        "test_rows": int(len(test)), "test_late_rate": round(float(y.mean()), 4),
        "baseline_zone_rate": {"pr_auc": round(average_precision_score(y, p_base), 4),
                               "roc_auc": round(roc_auc_score(y, p_base), 4),
                               "recall_at_30pct_precision": round(recall_at_precision(y, p_base), 4)},
        "gradient_boosting": {"pr_auc": round(average_precision_score(y, p_model), 4),
                              "roc_auc": round(roc_auc_score(y, p_model), 4),
                              "recall_at_30pct_precision": round(recall_at_precision(y, p_model), 4)},
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/model_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))

    # zone risk table for the dashboard: share of a zone's test packages the model flags
    flag = p_model >= np.quantile(p_model, 0.95)
    risk = (test_h.assign(flagged=flag).groupby(["station_code", "zone_id"])
            .agg(packages=("is_late", "size"), late_rate=("is_late", "mean"), flagged_share=("flagged", "mean"))
            .reset_index().query("packages >= 30"))
    with psycopg.connect(cfg.pg_dsn) as conn, conn.cursor() as cur:
        cur.execute("""create table if not exists mart.zone_risk (station_code text, zone_id text, packages int,
                       late_rate float8, flagged_share float8, scored_at timestamptz default now())""")
        cur.execute("truncate mart.zone_risk")
        cur.executemany("insert into mart.zone_risk (station_code, zone_id, packages, late_rate, flagged_share) "
                        "values (%s, %s, %s, %s, %s)", risk.itertuples(index=False, name=None))


if __name__ == "__main__":
    main()
