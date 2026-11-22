import os
import pymssql
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# تنظیمات SQL Server منبع
MSSQL_SERVER = os.getenv("SQLSERVER_HOST", "172.28.176.1")
MSSQL_DATABASE = os.getenv("SQLSERVER_DB", "Students_OP")
MSSQL_USER = os.getenv("SQLSERVER_USER", "sa")
MSSQL_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "")

# تنظیمات PostgreSQL Staging
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5433")
PG_DB = os.getenv("POSTGRES_DB", "staging_db")
PG_USER = os.getenv("POSTGRES_USER", "postgres_user")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password")

# نگاشت دقیق جدول‌های موجود در SQL Server به جدول‌های Staging
TABLES = [
    ("CourseOfferings", "stg_course_offerings_bridge"),
    ("DegreeRequirements", "stg_degree_requirements"),
    ("Applicants", "stg_dim_applicants"),
    ("Applicants", "stg_fact_applicants"),
    ("ClassStandings", "stg_dim_class_standings"),
    ("Courses", "stg_dim_courses"),
    ("DegreeLevels", "stg_dim_degree_levels"),
    ("Degrees", "stg_dim_degrees"),
    ("Departments", "stg_dim_departments"),
    ("Sessions", "stg_dim_sessions"),
    ("Students", "stg_dim_students"),
    ("Terms", "stg_dim_terms"),
    ("CourseEnrollments", "stg_fact_course_enrollments"),
    ("CourseOfferings", "stg_fact_course_offerings")
]

def extract_to_staging():
    print("--- Starting Extraction: SQL Server -> PostgreSQL Staging ---")
    try:
        mssql_conn = pymssql.connect(server=MSSQL_SERVER, user=MSSQL_USER, password=MSSQL_PASSWORD, database=MSSQL_DATABASE)
        mssql_cursor = mssql_conn.cursor()

        pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASSWORD)
        pg_cursor = pg_conn.cursor()

        for src_table, stg_table in TABLES:
            print(f"Extracting [{src_table}] -> [{stg_table}]...")
            
            try:
                mssql_cursor.execute(f"SELECT * FROM dbo.{src_table};")
                rows = mssql_cursor.fetchall()
            except Exception as e:
                print(f"Skipping {src_table} due to error: {e}")
                continue
            
            if not rows:
                print(f"Source table {src_table} is empty. Skipping.")
                continue

            columns = [column[0] for column in mssql_cursor.description]
            
            col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
            pg_cursor.execute(f"DROP TABLE IF EXISTS {stg_table} CASCADE;")
            pg_cursor.execute(f"CREATE TABLE {stg_table} ({col_defs});")
            pg_conn.commit()

            placeholders = ", ".join(["%s"] * len(columns))
            col_names_quoted = ", ".join([f'"{col}"' for col in columns])
            insert_query = f"INSERT INTO {stg_table} ({col_names_quoted}) VALUES ({placeholders})"
            
            stringified_rows = [[str(val) if val is not None else None for val in row] for row in rows]
            
            pg_cursor.executemany(insert_query, stringified_rows)
            pg_conn.commit()
            print(f"Successfully loaded {len(rows)} rows into [{stg_table}].")

        mssql_cursor.close()
        mssql_conn.close()
        pg_cursor.close()
        pg_conn.close()
        print("--- Extraction Completed Successfully! ---")

    except Exception as e:
        print(f"Error during extraction: {e}")

if __name__ == "__main__":
    extract_to_staging()
