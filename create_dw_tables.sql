CREATE DATABASE IF NOT EXISTS dw_db;

-- 1. CourseOfferings
CREATE TABLE IF NOT EXISTS dw_db.CourseOfferings (
    CourceOfferingKey Int32,
    DepartmentKey Int8,
    TermKey Int16,
    CourseKey Int16,
    Section Int32
) ENGINE = MergeTree() ORDER BY CourceOfferingKey;

-- 2. DegreeRequirements
CREATE TABLE IF NOT EXISTS dw_db.DegreeRequirements (
    RequirementKey Int32,
    RequirementAlternateKey Int32,
    DegreeKey Int16,
    ClassStandingKey Int8,
    SessionKey Int8,
    DepartmentKey Int8,
    CourseNumber Int32
) ENGINE = MergeTree() ORDER BY RequirementKey;

-- 3. DimApplicants
CREATE TABLE IF NOT EXISTS dw_db.DimApplicants (
    ApplicantKey Int32,
    ApplicantAlternateKey Int32,
    GeographyKey Int32,
    FirstName String,
    MiddleName String,
    LastName String,
    Gender String,
    StreetAddress String,
    Telephone String,
    Email String,
    DateOfBirth Date,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY ApplicantKey;

-- 4. DimApplicantTypes
CREATE TABLE IF NOT EXISTS dw_db.DimApplicantTypes (
    ApplicationTypeKey Int8,
    ApplicationType String,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY ApplicationTypeKey;

-- 5. DimClassStandings
CREATE TABLE IF NOT EXISTS dw_db.DimClassStandings (
    ClassStandingKey Int8,
    ClassStandingAlternatKey String,
    DegreeLevelKey Int8,
    ClassStandingName String,
    RequiredCredits Int32,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY ClassStandingKey;

-- 6. DimCourses
CREATE TABLE IF NOT EXISTS dw_db.DimCourses (
    CourseKey Int16,
    CourseAlternateKey Int32,
    DepartmentKey Int8,
    CourseTitle String,
    CourseDescription String,
    Credits Decimal(3,1),
    MaximumSectionSize Nullable(Int32),
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY CourseKey;

-- 7. DimDate
CREATE TABLE IF NOT EXISTS dw_db.DimDate (
    DateKey Int32,
    FullDateAlternateKey String,
    CalendarYear Int16,
    MonthNumberOfYear Int8,
    MonthName String,
    DayOfWeek Int16,
    DayOfWeekName String,
    CalendarSeason Int8,
    SeasonName Nullable(String),
    PersianDateKey Int32,
    PersianFullDateAlternateKey String,
    PersianCalendarYear Int16,
    PersianMonthNumberOfYear Int8,
    PersianMonthName String,
    PersianDayOfWeek Int16,
    PersianDayOfWeekName String,
    PersianCalendarSeason Int8,
    PersianSeasonName Nullable(String)
) ENGINE = MergeTree() ORDER BY DateKey;

-- 8. DimDegreeLevels
CREATE TABLE IF NOT EXISTS dw_db.DimDegreeLevels (
    DegreeLevelKey Int8,
    DegreeLevelAlternateKey String,
    DegreeType String,
    DegreeLevelName String,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY DegreeLevelKey;

-- 9. DimDegrees
CREATE TABLE IF NOT EXISTS dw_db.DimDegrees (
    DegreeKey Int16,
    DegreeAlternateKey Int32,
    DepartmentKey Int8,
    DegreeLevelKey Int8,
    DegreeName String,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY DegreeKey;

-- 10. DimDepartments
CREATE TABLE IF NOT EXISTS dw_db.DimDepartments (
    DepartmentKey Int8,
    DepartmentAlternateKey String,
    DepartmentName String,
    StartDate Date,
    EndDa Nullable(Date)
) ENGINE = MergeTree() ORDER BY DepartmentKey;

-- 11. DimGeography
CREATE TABLE IF NOT EXISTS dw_db.DimGeography (
    GeographyKey Int32,
    State String,
    City String,
    ZipCode String
) ENGINE = MergeTree() ORDER BY GeographyKey;

-- 12. DimSessions
CREATE TABLE IF NOT EXISTS dw_db.DimSessions (
    SessionKey Int8,
    SessionAlternateKey String,
    SessionName String,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY SessionKey;

-- 13. DimStudents
CREATE TABLE IF NOT EXISTS dw_db.DimStudents (
    StudentKey Int32,
    StudentAlternateKey Int32,
    GeographyKey Int32,
    FirstName String,
    MiddleName String,
    LastName String,
    Gender String,
    StreetAddress String,
    Telephone String,
    email String,
    DateOfBirth Date,
    StudentStatus String,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY StudentKey;

-- 14. DimTerms
CREATE TABLE IF NOT EXISTS dw_db.DimTerms (
    TermKey Int16,
    TermAlternateKey String,
    SessionKey Int8,
    Year Int32,
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY TermKey;

-- 15. FactApplicants
CREATE TABLE IF NOT EXISTS dw_db.FactApplicants (
    ApplicationID Int32,
    ApplicantKey Int32,
    ApplicationReceivedDateKey Int32,
    EntryTermKey Int16,
    ApplicationTypeKey Int8,
    Gpa Nullable(Decimal(3,2)),
    SatMathScore Nullable(Int32),
    SatReadingScore Nullable(Int32),
    SatWritingScore Nullable(Int32),
    EssayScore Nullable(Int32),
    ApplicationStatus String,
    AdmissionPoints Nullable(Float64),
    StartDate Date,
    EndDate Nullable(Date)
) ENGINE = MergeTree() ORDER BY ApplicationID;

-- 16. FactCourseEnrollments
CREATE TABLE IF NOT EXISTS dw_db.FactCourseEnrollments (
    CourseEnrollmentId Int32,
    StudentKey Int32,
    CourseOfferingKey Int32,
    ClassStandingKey Int8,
    DegreePursuedKey Int16,
    Grade Nullable(String),
    Point Decimal(2,1),
    IncludeInGpa Nullable(UInt8)
) ENGINE = MergeTree() ORDER BY CourseEnrollmentId;

-- 17. FactCourseOfferings
CREATE TABLE IF NOT EXISTS dw_db.FactCourseOfferings (
    CourseOfferingId Int32,
    CourseOfferingKey Int32,
    Capacity Int32
) ENGINE = MergeTree() ORDER BY CourseOfferingId;
