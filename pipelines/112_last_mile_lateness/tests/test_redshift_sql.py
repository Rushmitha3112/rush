from pathlib import Path

from lastmile.redshift_loader import split_sql

SQL = (Path(__file__).parents[1] / "sql/redshift/load_partition.sql").read_text()


def test_every_statement_survives_the_split():
    stmts = split_sql(SQL)
    # header comments sit right above the first create, an earlier version dropped it
    assert stmts[0].startswith("create temp table stage_pkg_raw")
    assert len(stmts) == 11
    assert sum(s.startswith("delete from") for s in stmts) == 2


def test_placeholders_all_filled():
    filled = SQL.format(run_date="2018-07-27", date_key="20180727", curated="s3://b", iam_role="arn:aws:iam::1:role/r")
    assert "{" not in filled
