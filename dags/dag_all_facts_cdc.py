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

PG = dict(host="localhost", port=5433, database="staging_db", user="postgres_user", password="postgres_password")
CH = dict(host="localhost", port=8124, username="admin", password="admin_password", database="dw_db")
pg_c = lambda: psycopg2.connect(**PG)
ch_c = lambda: clickhouse_connect.get_client(**CH)

def cdc_offerings(**context):
    pg, ch = pg_c(), ch_c()
    try:
        co = pd.read_sql("SELECT * FROM stg_course_offerings", con=pg)
        curr = {int(r[0]): int(r[1] or 0) for r in ch.query("SELECT CourseOfferingId,Capacity FROM FactCourseOfferings").result_rows}
        upd, rows = [], []
        for r in co.itertuples(index=False):
            oid, cap = int(r.course_offering_id or 0), int(r.capacity or 30)
            if oid not in curr or curr[oid] != cap:
                if oid in curr: upd.append(oid)
                rows.append((oid, oid, cap))
        if upd: ch.command(f"ALTER TABLE FactCourseOfferings DELETE WHERE CourseOfferingId IN ({','.join(map(str,set(upd)))})")
        if rows: ch.insert("FactCourseOfferings", rows, column_names=["CourseOfferingId","CourseOfferingKey","Capacity"])
        print("CDC_FOFF_OK:", len(rows))
    finally: pg.close()

def cdc_enrollments(**context):
    pg, ch = pg_c(), ch_c()
    try:
        smap = {str(r[0]).strip(): int(r[1]) for r in ch.query("SELECT StudentAlternateKey,StudentKey FROM DimStudents WHERE EndDate IS NULL").result_rows}
        gr = pd.read_sql("SELECT * FROM stg_grades", con=pg)
        gpts = {str(r.grade).strip(): float(r.points or 0.0) for r in gr.itertuples(index=False)}
        ginc = {str(r.grade).strip(): int(r.include_in_gpa or 1) for r in gr.itertuples(index=False)}
        curr = {int(r[0]): (None if r[1] is None else str(r[1])) for r in ch.query("SELECT CourseEnrollmentId,Grade FROM FactCourseEnrollments").result_rows}
        upd, rows = [], []
        cols = ["CourseEnrollmentId","StudentKey","CourseOfferingKey","ClassStandingKey","DegreePursuedKey","Grade","Point","IncludeInGpa"]
        for c in pd.read_sql("SELECT course_enrollment_id,course_offering_id,student_id,grade FROM stg_course_enrollments", con=pg, chunksize=250000):
            for r in c.itertuples(index=False):
                eid, gv = int(r.course_enrollment_id or 0), (None if pd.isna(r.grade) else str(r.grade))
                if eid not in curr or curr[eid] != gv:
                    if eid in curr: upd.append(eid)
                    rows.append((eid, smap.get(str(r.student_id).strip(),1), int(r.course_offering_id or 1), 1, 1, gv, gpts.get(str(r.grade).strip(),0.0) if gv else 0.0, ginc.get(str(r.grade).strip(),1) if gv else 0))
        if upd: ch.command(f"ALTER TABLE FactCourseEnrollments DELETE WHERE CourseEnrollmentId IN ({','.join(map(str,set(upd)))})")
        for i in range(0, len(rows), 250000): ch.insert("FactCourseEnrollments", rows[i:i+250000], column_names=cols)
        print("CDC_FENR_OK:", len(rows))
    finally: pg.close()

def cdc_applicants(**context):
    pg, ch, d0 = pg_c(), ch_c(), date.today()
    try:
        amap = {str(r[0]).strip(): int(r[1]) for r in ch.query("SELECT ApplicantAlternateKey,ApplicantKey FROM DimApplicants WHERE EndDate IS NULL").result_rows}
        tmap = {str(r[0]).strip(): int(r[1]) for r in ch.query("SELECT TermAlternateKey,TermKey FROM DimTerms").result_rows}
        atmap = {str(r[1]).strip(): int(r[0]) for r in ch.query("SELECT ApplicationTypeKey,ApplicationType FROM DimApplicantTypes").result_rows}
        curr = {int(r[0]): str(r[1] or "") for r in ch.query("SELECT ApplicationID,ApplicationStatus FROM FactApplicants").result_rows}
        upd, rows = [], []
        cols = ["ApplicationID","ApplicantKey","ApplicationReceivedDateKey","EntryTermKey","ApplicationTypeKey","Gpa","SatMathScore","SatReadingScore","SatWritingScore","EssayScore","ApplicationStatus","AdmissionPoints","StartDate","EndDate"]
        for c in pd.read_sql("SELECT * FROM stg_applicants", con=pg, chunksize=150000):
            dt = pd.to_datetime(c["application_received_date"], errors="coerce")
            dk = [20200101 if pd.isna(x) else int(x.strftime("%Y%m%d")) for x in dt]
            for idx, r in enumerate(c.itertuples(index=False)):
                aid, st = int(r.applicant_id or 0), str(r.application_status or "Pending")
                if aid not in curr or curr[aid] != st:
                    if aid in curr: upd.append(aid)
                    rows.append((aid, amap.get(str(r.applicant_id).strip(),1), dk[idx], tmap.get(str(r.entry_term).strip(),1), atmap.get(str(r.application_type).strip(),1), None if pd.isna(r.gpa) else float(r.gpa), None if pd.isna(r.sat_math_score) else int(r.sat_math_score), None if pd.isna(r.sat_reading_score) else int(r.sat_reading_score), None if pd.isna(r.sat_writing_score) else int(r.sat_writing_score), None if pd.isna(r.essay_score) else int(r.essay_score), st, None if pd.isna(r.admission_points) else float(r.admission_points), d0, None))
        if upd: ch.command(f"ALTER TABLE FactApplicants DELETE WHERE ApplicationID IN ({','.join(map(str,set(upd)))})")
        for i in range(0, len(rows), 150000): ch.insert("FactApplicants", rows[i:i+150000], column_names=cols)
        print("CDC_FAPP_OK:", len(rows))
    finally: pg.close()
