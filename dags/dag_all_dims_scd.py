import os
from datetime import datetime, timedelta, date
import psycopg2, pandas as pd, clickhouse_connect
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    class DAG:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    class PythonOperator:
        def __init__(self, *a, **kw): self.fn = kw.get('python_callable')
        def __rshift__(self, other): return other


PG = dict(host="localhost", port=5433, database="staging_db",
          user="postgres_user", password="postgres_password")
CH = dict(host="localhost", port=8124, username="admin",
          password="admin_password", database="dw_db")
pg_c = lambda: psycopg2.connect(**PG)
ch_c = lambda: clickhouse_connect.get_client(**CH)
def run_scd1(**context):
    pg, ch, d0 = pg_c(), ch_c(), date.today()
    try:
        for tbl, q, cols in [
            ("DimSessions", "SELECT * FROM stg_sessions", ["SessionKey","SessionAlternateKey","SessionName","StartDate","EndDate"]),
            ("DimDegreeLevels", "SELECT * FROM stg_degree_levels", ["DegreeLevelKey","DegreeLevelAlternateKey","DegreeType","DegreeLevelName","StartDate","EndDate"]),
        ]:
            df = pd.read_sql(q, con=pg)
            if not df.empty:
                rows = [(i+1, str(r[1]), "Degree" if tbl=="DimDegreeLevels" else None, str(r[2]), d0, None) if tbl=="DimDegreeLevels" else (i+1, str(r[1]), str(r[2]), d0, None) for i,r in enumerate(df.itertuples(index=False))]
                ch.command(f"TRUNCATE TABLE IF EXISTS {tbl}")
                ch.insert(tbl, rows, column_names=cols)
        print("SCD1_OK")
    finally:
        pg.close()
def run_scd2(**context):
    pg, ch, d0 = pg_c(), ch_c(), date.today()
    try:
        act = {int(r[0]): str(r[1] or "") for r in ch.query("SELECT StudentAlternateKey,StudentStatus FROM DimStudents WHERE EndDate IS NULL").result_rows}
        mk = ch.query("SELECT coalesce(max(StudentKey),0) FROM DimStudents").result_rows[0][0]
        closed, ins = [], []
        for c in pd.read_sql("SELECT * FROM stg_students", con=pg, chunksize=100000):
            for r in c.itertuples(index=False):
                sid, st = int(r.student_id or 0), str(r.student_status or "")
                if sid not in act or act[sid] != st:
                    if sid in act: closed.append(sid)
                    mk += 1
                    ins.append((mk, sid, 1, str(r.first_name or ""), str(r.middle_name or ""), str(r.last_name or ""), str(r.gender or ""), str(r.street_address or ""), str(r.telephone or ""), str(r.email or ""), None, st, d0, None))
        if closed:
            ch.command(f"ALTER TABLE DimStudents UPDATE EndDate=toDate('{d0}') WHERE StudentAlternateKey IN ({','.join(map(str,set(closed)))}) AND EndDate IS NULL")
        if ins:
            ch.insert("DimStudents", ins, column_names=["StudentKey","StudentAlternateKey","GeographyKey","FirstName","MiddleName","LastName","Gender","StreetAddress","Telephone","email","DateOfBirth","StudentStatus","StartDate","EndDate"])
        print("SCD2_OK:", len(ins))
    finally:
        pg.close()

with DAG("dag_all_dims_scd", default_args={"owner":"farzane","retries":1,"retry_delay":timedelta(minutes=2)},
         start_date=datetime(2026,11,1), schedule="@daily", catchup=False) as dag:
    PythonOperator(task_id="scd1", python_callable=run_scd1) >> PythonOperator(task_id="scd2", python_callable=run_scd2)
