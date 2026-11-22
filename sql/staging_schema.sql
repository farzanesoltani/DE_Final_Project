-- Drop tables if they exist (in correct reverse dependency order)
DROP TABLE IF EXISTS stg_course_enrollments CASCADE;
DROP TABLE IF EXISTS stg_course_offerings CASCADE;
DROP TABLE IF EXISTS stg_courses CASCADE;
DROP TABLE IF EXISTS stg_student_profiles CASCADE;
DROP TABLE IF EXISTS stg_students CASCADE;
DROP TABLE IF EXISTS stg_applicants CASCADE;
DROP TABLE IF EXISTS stg_degree_requirements CASCADE;
DROP TABLE IF EXISTS stg_degrees CASCADE;
DROP TABLE IF EXISTS stg_degree_types CASCADE;
DROP TABLE IF EXISTS stg_class_standings CASCADE;
DROP TABLE IF EXISTS stg_degree_levels CASCADE;
DROP TABLE IF EXISTS stg_terms CASCADE;
DROP TABLE IF EXISTS stg_sessions CASCADE;
DROP TABLE IF EXISTS stg_departments CASCADE;
DROP TABLE IF EXISTS stg_grades CASCADE;

-- 1. Terms
CREATE TABLE stg_terms (
    term_code VARCHAR(6) PRIMARY KEY,
    session_code VARCHAR(2),
    year INT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Sessions
CREATE TABLE stg_sessions (
    session_code VARCHAR(2) PRIMARY KEY,
    session_name VARCHAR(10),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Departments
CREATE TABLE stg_departments (
    department_code VARCHAR(2) PRIMARY KEY,
    department_name VARCHAR(25),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Degree Levels
CREATE TABLE stg_degree_levels (
    degree_level_code VARCHAR(1) PRIMARY KEY,
    degree_level_name VARCHAR(20),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Degree Types
CREATE TABLE stg_degree_types (
    degree_type_code VARCHAR(3) PRIMARY KEY,
    degree_type_name VARCHAR(25),
    degree_level_code VARCHAR(1),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Degrees
CREATE TABLE stg_degrees (
    degree_id INT PRIMARY KEY,
    department_code VARCHAR(2),
    degree_type_code VARCHAR(3),
    degree_name VARCHAR(64),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Class Standings
CREATE TABLE stg_class_standings (
    class_standing_code VARCHAR(2) PRIMARY KEY,
    class_standing_name VARCHAR(25),
    degree_level_code VARCHAR(1),
    required_credits INT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Grades
CREATE TABLE stg_grades (
    grade VARCHAR(1) PRIMARY KEY,
    points DECIMAL(2, 1),
    include_in_gpa BOOLEAN,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Courses
CREATE TABLE stg_courses (
    department_code VARCHAR(2),
    course_number INT,
    course_title VARCHAR(64),
    course_description VARCHAR(512),
    credits DECIMAL(3, 1),
    maximum_section_size INT,
    PRIMARY KEY (department_code, course_number),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Course Offerings
CREATE TABLE stg_course_offerings (
    course_offering_id INT PRIMARY KEY,
    department_code VARCHAR(2),
    course_number INT,
    term_code VARCHAR(6),
    section INT,
    capacity INT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Students (Dimension Source)
CREATE TABLE stg_students (
    student_id INT PRIMARY KEY,
    first_name VARCHAR(40),
    middle_name VARCHAR(40),
    last_name VARCHAR(40),
    gender VARCHAR(1),
    street_address VARCHAR(50),
    city VARCHAR(30),
    state VARCHAR(2),
    zip_code VARCHAR(5),
    telephone VARCHAR(20),
    email VARCHAR(80),
    date_of_birth DATE,
    degree_pursued INT,
    class_standing_code VARCHAR(2),
    student_status VARCHAR(1),
    enrollment_term VARCHAR(6),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    op_action VARCHAR(10)
);

-- 12. Applicants
CREATE TABLE stg_applicants (
    applicant_id INT PRIMARY KEY,
    first_name VARCHAR(40),
    middle_name VARCHAR(40),
    last_name VARCHAR(40),
    gender VARCHAR(1),
    street_address VARCHAR(50),
    city VARCHAR(30),
    state VARCHAR(2),
    zip_code VARCHAR(5),
    telephone VARCHAR(20),
    email VARCHAR(80),
    date_of_birth DATE,
    application_received_date DATE,
    entry_term VARCHAR(6),
    application_type VARCHAR(1),
    gpa DECIMAL(3, 2),
    sat_math_score INT,
    sat_reading_score INT,
    sat_writing_score INT,
    essay_score INT,
    application_status VARCHAR(1),
    admission_points FLOAT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    op_action VARCHAR(10)
);

-- 13. Student Profiles
CREATE TABLE stg_student_profiles (
    student_id INT PRIMARY KEY,
    profile_id INT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. Degree Requirements
CREATE TABLE stg_degree_requirements (
    requirement_id INT PRIMARY KEY,
    degree_id INT,
    class_standing_code VARCHAR(2),
    session_code VARCHAR(2),
    department_code VARCHAR(2),
    course_number INT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Course Enrollments (Fact Table Source)
CREATE TABLE stg_course_enrollments (
    course_enrollment_id INT PRIMARY KEY,
    course_offering_id INT,
    student_id INT,
    grade VARCHAR(1),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    op_action VARCHAR(10)
);
