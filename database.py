import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "carematch.db" if os.name == "nt" else "/tmp/carematch.db"
DB_PATH = os.environ.get("DB_PATH", DEFAULT_DB_PATH)


def get_connection():
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            location TEXT NOT NULL,
            condition TEXT NOT NULL,
            password TEXT,
            income_range TEXT,
            insurance_level TEXT,
            budget_preference REAL NOT NULL,
            blood_group TEXT,
            allergies TEXT,
            medical_conditions TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Hospital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            specialization TEXT NOT NULL,
            rating REAL NOT NULL,
            avg_cost REAL NOT NULL,
            emergency_capable INTEGER NOT NULL DEFAULT 0,
            ambulance_available INTEGER NOT NULL DEFAULT 0,
            ambulance_number TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Doctor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hospital_id INTEGER NOT NULL,
            specialization TEXT NOT NULL,
            experience_years INTEGER NOT NULL,
            rating REAL NOT NULL,
            contact TEXT,
            email TEXT,
            password TEXT,
            hospital TEXT,
            created_at TEXT,
            is_portal_doctor INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (hospital_id) REFERENCES Hospital (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS DoctorPatientLink (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES Doctor (id),
            FOREIGN KEY (patient_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS DoctorPrescription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            medicine_name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            instructions TEXT,
            start_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES Doctor (id),
            FOREIGN KEY (patient_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS FamilyMember (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            relationship TEXT NOT NULL,
            contact TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PatientDoctorLink (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES User (id),
            FOREIGN KEY (doctor_id) REFERENCES Doctor (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Questionnaire (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES Doctor (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            questionnaire_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            FOREIGN KEY (questionnaire_id) REFERENCES Questionnaire (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Answer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES Question (id),
            FOREIGN KEY (user_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Medicine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            schedule TEXT NOT NULL,
            taken_count INTEGER NOT NULL DEFAULT 0,
            total_count INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS HealthLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sleep_hours REAL NOT NULL,
            stress_level INTEGER NOT NULL,
            energy_level INTEGER NOT NULL,
            symptoms TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PatientState (
            user_id INTEGER PRIMARY KEY,
            stress_score INTEGER NOT NULL,
            energy_score INTEGER NOT NULL,
            trend TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_assessment_at TEXT,
            next_assessment_due TEXT,
            risk_level TEXT,
            risk_probability INTEGER,
            risk_reason TEXT,
            recommendation TEXT,
            FOREIGN KEY (user_id) REFERENCES User (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS QuestionBank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condition TEXT NOT NULL,
            category TEXT NOT NULL,
            question_text TEXT NOT NULL,
            weight INTEGER NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PatientAnswer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_value INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES User (id),
            FOREIGN KEY (question_id) REFERENCES QuestionBank (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS AssessmentHistory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User (id)
        )
        """
    )

    conn.commit()


def _add_column_if_missing(conn, table_name, column_name, column_ddl):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = [dict(row) for row in cursor.fetchall()]
    existing_columns = {row["name"] for row in rows}

    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_ddl}")


def migrate_schema(conn):
    # Safe, additive migrations only.
    _add_column_if_missing(conn, "User", "password", "TEXT")
    _add_column_if_missing(conn, "User", "blood_group", "TEXT")
    _add_column_if_missing(conn, "User", "allergies", "TEXT")
    _add_column_if_missing(conn, "User", "medical_conditions", "TEXT")
    _add_column_if_missing(conn, "User", "emergency_contact_name", "TEXT")
    _add_column_if_missing(conn, "User", "emergency_contact_phone", "TEXT")

    _add_column_if_missing(
        conn,
        "Hospital",
        "emergency_capable",
        "INTEGER NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(
        conn,
        "Hospital",
        "ambulance_available",
        "INTEGER NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(conn, "Hospital", "ambulance_number", "TEXT")
    _add_column_if_missing(conn, "Doctor", "contact", "TEXT")
    _add_column_if_missing(conn, "Doctor", "email", "TEXT")
    _add_column_if_missing(conn, "Doctor", "password", "TEXT")
    _add_column_if_missing(conn, "Doctor", "hospital", "TEXT")
    _add_column_if_missing(conn, "Doctor", "created_at", "TEXT")
    _add_column_if_missing(conn, "Doctor", "is_portal_doctor", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "PatientState", "risk_level", "TEXT")
    _add_column_if_missing(conn, "PatientState", "risk_probability", "INTEGER")
    _add_column_if_missing(conn, "PatientState", "risk_reason", "TEXT")
    _add_column_if_missing(conn, "PatientState", "recommendation", "TEXT")
    _add_column_if_missing(conn, "PatientState", "last_assessment_at", "TEXT")
    _add_column_if_missing(conn, "PatientState", "next_assessment_due", "TEXT")

    conn.commit()


def seed_hospitals_and_doctors(conn):
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM Hospital")
    hospital_count = cursor.fetchone()["count"]

    if hospital_count > 0:
        return

    hospitals = [
        (
            "CityCare Multispeciality",
            "Bengaluru",
            "cardiology",
            4.6,
            3200,
            1,
            1,
            "+91-9876500011",
        ),
        (
            "Sunrise Neuro Center",
            "Bengaluru",
            "neurology",
            4.4,
            4500,
            1,
            1,
            "+91-9876500012",
        ),
        (
            "GreenLife General Hospital",
            "Mysuru",
            "general",
            4.2,
            2100,
            1,
            0,
            "+91-9876500013",
        ),
        (
            "Hope Oncology Institute",
            "Chennai",
            "oncology",
            4.7,
            5200,
            1,
            1,
            "+91-9876500014",
        ),
        (
            "WellSpring Ortho Clinic",
            "Bengaluru",
            "orthopedics",
            4.3,
            2800,
            1,
            1,
            "+91-9876500015",
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO Hospital (
            name,
            location,
            specialization,
            rating,
            avg_cost,
            emergency_capable,
            ambulance_available,
            ambulance_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        hospitals,
    )

    cursor.execute("SELECT id, specialization FROM Hospital")
    hospital_rows = [dict(row) for row in cursor.fetchall()]

    doctors = []
    for row in hospital_rows:
        hospital_id = row["id"]
        specialization = row["specialization"]
        doctors.extend(
            [
                (
                    f"Dr. {specialization.title()} Expert A",
                    hospital_id,
                    specialization,
                    14,
                    4.7,
                ),
                (
                    f"Dr. {specialization.title()} Expert B",
                    hospital_id,
                    specialization,
                    9,
                    4.4,
                ),
            ]
        )

    cursor.executemany(
        """
        INSERT INTO Doctor (name, hospital_id, specialization, experience_years, rating, contact)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                name,
                hospital_id,
                specialization,
                experience_years,
                rating,
                f"+91-98989{hospital_id:02d}{idx:02d}",
            )
            for idx, (name, hospital_id, specialization, experience_years, rating) in enumerate(doctors, start=1)
        ],
    )

    conn.commit()


def backfill_emergency_hospital_data(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE Hospital
        SET emergency_capable = COALESCE(emergency_capable, 1),
            ambulance_available = COALESCE(ambulance_available, 1),
            ambulance_number = COALESCE(
                ambulance_number,
                '+91-900000' || printf('%04d', id)
            )
        """
    )
    conn.commit()


def backfill_doctor_contact_data(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE Doctor
        SET contact = COALESCE(contact, '+91-988000' || printf('%04d', id))
        """
    )
    conn.commit()


def seed_question_bank(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM QuestionBank")
    existing = cursor.fetchone()["count"]

    if existing > 0:
        return

    seed_questions = [
        ("cardiology", "stress", "Do you feel chest tightness when stressed?", 8),
        (
            "cardiology",
            "energy",
            "Do you feel unusually fatigued after minor activity?",
            7,
        ),
        ("diabetes", "stress", "Do you feel dizziness when stressed?", 7),
        ("diabetes", "energy", "Do you feel sudden weakness?", 6),
        ("general", "stress", "Do you feel mentally overwhelmed?", 5),
        ("general", "energy", "How energetic do you feel today?", 5),
    ]

    cursor.executemany(
        """
        INSERT INTO QuestionBank (condition, category, question_text, weight)
        VALUES (?, ?, ?, ?)
        """,
        seed_questions,
    )
    conn.commit()


def init_db():
    conn = get_connection()
    create_tables(conn)
    migrate_schema(conn)
    seed_hospitals_and_doctors(conn)
    backfill_emergency_hospital_data(conn)
    backfill_doctor_contact_data(conn)
    seed_question_bank(conn)
    conn.close()
