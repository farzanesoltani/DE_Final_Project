import os
import traceback
from datetime import date, timedelta
import psycopg2
import pandas as pd
import clickhouse_connect
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
PG_DB = os.getenv("POSTGRES_DB", "staging_db")
PG_USER = os.getenv("POSTGRES_USER", "postgres_user")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password")

CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8124"))
CH_USER = os.getenv("CLICKHOUSE_USER", "admin")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "admin_password")
CH_DB = os.getenv("CLICKHOUSE_DB", "dw_db")


def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASSWORD
    )


def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD, database=CH_DB
    )


def get_pg_tables(pg):
    cur = pg.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    res = {r[0].lower(): r[0] for r in cur.fetchall()}
    cur.close()
    return res


def read_stg(pg, pg_tables, name):
    key = name.lower()
    if key not in pg_tables:
        return pd.DataFrame()
    actual = pg_tables[key]
    df = pd.read_sql(f'SELECT * FROM "{actual}"', con=pg)
    print(f"  Read {len(df):,} rows from [{actual}].")
    return df


def find_col(df, candidates):
    if df.empty:
        return None
    low_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in low_map:
            return low_map[c.lower()]
    return None


def col_list(df, candidates, default="", as_int=False, as_float=False):
    n = len(df)
    col = find_col(df, candidates)
    if col is None:
        return [default] * n
    s = df[col]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    if as_int:
        fill_v = 0 if default is None else default
        nums = pd.to_numeric(s, errors="coerce").fillna(fill_v)
        return [int(x) for x in nums]
    if as_float:
        fill_v = 0.0 if default is None else default
        nums = pd.to_numeric(s, errors="coerce").fillna(fill_v)
        return [float(x) for x in nums]
    if default is None:
        return [None if pd.isna(x) else x for x in s]
    s = s.fillna(default)
    return ["" if pd.isna(x) else str(x) for x in s]


def cast_to_ch_schema(ch, table_name, df):
    desc = ch.query(f"DESCRIBE TABLE {table_name}").result_rows
    ch_cols = {r[0]: r[1] for r in desc}
    aligned = pd.DataFrame()
    for col_name, ch_type in ch_cols.items():
        if col_name not in df.columns:
            continue
        vals = [None if pd.isna(v) else v for v in df[col_name]]
        is_null = "Nullable(" in ch_type
        if "Int" in ch_type:
            aligned[col_name] = [
                (None if is_null else 0) if v is None or pd.isna(pd.to_numeric(v, errors="coerce"))
                else int(pd.to_numeric(v, errors="coerce"))
                for v in vals
            ]
        elif "Float" in ch_type or "Decimal" in ch_type:
            aligned[col_name] = [
                (None if is_null else 0.0) if v is None or pd.isna(pd.to_numeric(v, errors="coerce"))
                else float(pd.to_numeric(v, errors="coerce"))
                for v in vals
            ]
        elif "DateTime" in ch_type:
            ts = pd.to_datetime(pd.Series(vals), errors="coerce")
            aligned[col_name] = [None if pd.isna(t) else t.to_pydatetime() for t in ts]
        elif "Date" in ch_type:
            dt = pd.to_datetime(pd.Series(vals), errors="coerce").dt.date
            aligned[col_name] = [None if pd.isna(d) else d for d in dt]
        else:
            aligned[col_name] = [(None if is_null else "") if v is None else str(v) for v in vals]
    return aligned


def load_table(ch, table_name, df):
    if df.empty:
        print(f"  [SKIP] [{table_name}] has no data.")
        return
    aligned = cast_to_ch_schema(ch, table_name, df)
    ch.command(f"TRUNCATE TABLE IF EXISTS {table_name}")
    ch.insert(table_name, list(aligned.itertuples(index=False, name=None)), column_names=list(aligned.columns))
    print(f"  [OK] Loaded {len(aligned):,} rows into [{table_name}].")


def fetch_lookup(ch, table, key_col, alt_col):
    try:
        rows = ch.query(f"SELECT {alt_col}, {key_col} FROM {table}").result_rows
        return {str(r[0]).strip(): int(r[1]) for r in rows if r[0] is not None and str(r[0]).strip() != ""}
    except Exception:
        return {}


def build_dim_date(start_d=date(2015, 1, 1), end_d=date(2028, 12, 31)):
    try:
        import jdatetime
        has_jdt = True
    except ImportError:
        has_jdt = False

    p_months = [
        "Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
        "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand",
    ]
    p_days = ["Shanbeh", "Yekshanbeh", "Doshanbeh", "Seshanbeh", "Chaharshanbeh", "Panjshanbeh", "Jomeh"]
    seasons = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Autumn"}

    rows = []
    cur = start_d
    while cur <= end_d:
        dk = int(cur.strftime("%Y%m%d"))
        sn = ((cur.month - 1) // 3) + 1
        sname = seasons[sn]
        if has_jdt:
            jd = jdatetime.date.fromgregorian(date=cur)
            pk = int(f"{jd.year:04d}{jd.month:02d}{jd.day:02d}")
            ps = ((jd.month - 1) // 3) + 1
            rows.append((
                dk, cur.strftime("%Y-%m-%d"), cur.year, cur.month, cur.strftime("%B"),
                cur.isoweekday(), cur.strftime("%A"), sn, sname,
                pk, jd.strftime("%Y-%m-%d"), jd.year, jd.month, p_months[jd.month - 1],
                jd.weekday() + 1, p_days[jd.weekday()], ps,
                ["Spring", "Summer", "Autumn", "Winter"][ps - 1],
            ))
        else:
            rows.append((
                dk, cur.strftime("%Y-%m-%d"), cur.year, cur.month, cur.strftime("%B"),
                cur.isoweekday(), cur.strftime("%A"), sn, sname,
                dk, cur.strftime("%Y-%m-%d"), cur.year, cur.month, cur.strftime("%B"),
                cur.isoweekday(), cur.strftime("%A"), sn, sname,
            ))
        cur += timedelta(days=1)

    cols = [
        "DateKey", "FullDateAlternateKey", "CalendarYear", "MonthNumberOfYear", "MonthName",
        "DayOfWeek", "DayOfWeekName", "CalendarSeason", "SeasonName",
        "PersianDateKey", "PersianFullDateAlternateKey", "PersianCalendarYear", "PersianMonthNumberOfYear",
        "PersianMonthName", "PersianDayOfWeek", "PersianDayOfWeekName", "PersianCalendarSeason", "PersianSeasonName",
    ]
    return pd.DataFrame(rows, columns=cols)

def load_all_tables():
    print("--- Starting Complete DW Transformation & Load ---")
    ch = get_ch_client()
    pg = get_pg_connection()
    try:
        pg_tables = get_pg_tables(pg)
        d0 = date(2020, 1, 1)
        lk = load_dimensions(ch, pg, pg_tables, d0)

        df_off = read_stg(pg, pg_tables, "stg_course_offerings_bridge")
        if df_off.empty: df_off = read_stg(pg, pg_tables, "stg_course_offerings")
        df_req = read_stg(pg, pg_tables, "stg_degree_requirements")
        df_foff = read_stg(pg, pg_tables, "stg_fact_course_offerings")
        df_fenr = read_stg(pg, pg_tables, "stg_fact_course_enrollments")
        df_fapp = read_stg(pg, pg_tables, "stg_fact_applicants")
        df_grades = read_stg(pg, pg_tables, "stg_grades")

        off_map = {}
        if not df_off.empty:
            n = len(df_off)
            off_keys = col_list(df_off, ["CourseOfferingId", "course_offering_id", "ID"], 0, as_int=True)
            if not off_keys or all(k == 0 for k in off_keys): off_keys = list(range(1, n + 1))
            load_table(ch, "CourseOfferings", pd.DataFrame({
                "CourceOfferingKey": off_keys,
                "DepartmentKey": [lk["dept"].get(x.strip(), 1) for x in col_list(df_off, ["DepartmentCode", "department_code"], "")],
                "TermKey": [lk["term"].get(x.strip(), 1) for x in col_list(df_off, ["TermCode", "term_code"], "")],
                "CourseKey": [lk["crs"].get(x.strip(), 1) for x in col_list(df_off, ["CourseNumber", "course_number"], "")],
                "Section": col_list(df_off, ["Section", "section"], 1, as_int=True),
            }))
            off_map = {int(k): int(k) for k in off_keys}

        if not df_req.empty:
            n = len(df_req)
            req_ids = col_list(df_req, ["RequirementId", "requirement_id", "ID"], 0, as_int=True)
            if not req_ids or all(k == 0 for k in req_ids): req_ids = list(range(1, n + 1))
            load_table(ch, "DegreeRequirements", pd.DataFrame({
                "RequirementKey": list(range(1, n + 1)), "RequirementAlternateKey": req_ids,
                "DegreeKey": [lk["deg"].get(x.strip(), 1) for x in col_list(df_req, ["DegreeId", "degree_id"], "")],
                "ClassStandingKey": [lk["cs"].get(x.strip(), 1) for x in col_list(df_req, ["ClassStandingCode", "class_standing_code"], "")],
                "SessionKey": [lk["sess"].get(x.strip(), 1) for x in col_list(df_req, ["SessionCode", "session_code"], "")],
                "DepartmentKey": [lk["dept"].get(x.strip(), 1) for x in col_list(df_req, ["DepartmentCode", "department_code"], "")],
                "CourseNumber": col_list(df_req, ["CourseNumber", "course_number"], 0, as_int=True),
            }))

        src_foff = df_foff if not df_foff.empty else df_off
        if not src_foff.empty:
            n = len(src_foff)
            off_ids = col_list(src_foff, ["CourseOfferingId", "course_offering_id", "ID"], 0, as_int=True)
            if not off_ids or all(k == 0 for k in off_ids): off_ids = list(range(1, n + 1))
            load_table(ch, "FactCourseOfferings", pd.DataFrame({
                "CourseOfferingId": off_ids,
                "CourseOfferingKey": [off_map.get(int(oid), int(oid)) for oid in off_ids],
                "Capacity": col_list(src_foff, ["Capacity", "capacity", "MaximumSectionSize"], 30, as_int=True),
            }))

        if not df_fenr.empty:
            n = len(df_fenr)
            enr_ids = col_list(df_fenr, ["CourseEnrollmentId", "course_enrollment_id", "ID"], 0, as_int=True)
            stu_ids = col_list(df_fenr, ["StudentId", "student_id"], "")
            off_ids = col_list(df_fenr, ["CourseOfferingId", "course_offering_id"], 1, as_int=True)
            grades = col_list(df_fenr, ["Grade", "grade"], None)
            g_pts, g_inc = {}, {}
            if not df_grades.empty:
                for gc, gp, gi in zip(col_list(df_grades, ["grade", "Grade"], ""), col_list(df_grades, ["points", "Points", "point"], 0.0, as_float=True), col_list(df_grades, ["include_in_gpa", "IncludeInGpa"], 1, as_int=True)):
                    if gc.strip():
                        g_pts[gc.strip()] = gp
                        g_inc[gc.strip()] = gi
            load_table(ch, "FactCourseEnrollments", pd.DataFrame({
                "CourseEnrollmentId": enr_ids,
                "StudentKey": [lk["stu"].get(s.strip(), 1) for s in stu_ids],
                "CourseOfferingKey": [off_map.get(int(oid), int(oid)) for oid in off_ids],
                "ClassStandingKey": [lk["stu_cs"].get(s.strip(), 1) for s in stu_ids],
                "DegreePursuedKey": [lk["stu_deg"].get(s.strip(), 1) for s in stu_ids],
                "Grade": grades,
                "Point": [g_pts.get(str(g).strip(), 0.0) if g is not None else 0.0 for g in grades],
                "IncludeInGpa": [g_inc.get(str(g).strip(), 1) if g is not None else 0 for g in grades],
            }))

        if not df_fapp.empty:
            n = len(df_fapp)
            app_ids = col_list(df_fapp, ["ApplicantId", "applicant_id", "ApplicationID", "ID"], 0, as_int=True)
            appl_raw = col_list(df_fapp, ["ApplicantId", "applicant_id"], "")
            dt_s = pd.to_datetime(pd.Series(col_list(df_fapp, ["ApplicationReceivedDate", "application_received_date"], None)), errors="coerce")
            d_keys = [20200101 if pd.isna(d) else int(d.strftime("%Y%m%d")) for d in dt_s]
            load_table(ch, "FactApplicants", pd.DataFrame({
                "ApplicationID": app_ids,
                "ApplicantKey": [lk["appl"].get(x.strip(), 1) for x in appl_raw],
                "ApplicationReceivedDateKey": d_keys,
                "EntryTermKey": [lk["term"].get(x.strip(), 1) for x in col_list(df_fapp, ["EntryTerm", "entry_term", "TermCode"], "")],
                "ApplicationTypeKey": [lk["apptype"].get(x.strip(), 1) for x in col_list(df_fapp, ["ApplicationType", "application_type"], "")],
                "Gpa": col_list(df_fapp, ["Gpa", "gpa"], None, as_float=True),
                "SatMathScore": col_list(df_fapp, ["SatMathScore", "sat_math_score"], None, as_int=True),
                "SatReadingScore": col_list(df_fapp, ["SatReadingScore", "sat_reading_score"], None, as_int=True),
                "SatWritingScore": col_list(df_fapp, ["SatWritingScore", "sat_writing_score"], None, as_int=True),
                "EssayScore": col_list(df_fapp, ["EssayScore", "essay_score"], None, as_int=True),
                "ApplicationStatus": col_list(df_fapp, ["ApplicationStatus", "application_status"], "Pending"),
                "AdmissionPoints": col_list(df_fapp, ["AdmissionPoints", "admission_points"], None, as_float=True),
                "StartDate": [d0] * n, "EndDate": [None] * n,
            }))

        print("\n--- All DW Tables Loaded Successfully! ---")
    except Exception as e:
        print(f"\n❌ Error during full load: {e}")
        traceback.print_exc()
    finally:
        pg.close()


if __name__ == "__main__":
    load_all_tables()
