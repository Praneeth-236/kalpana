from database import get_connection


# User model operations

def create_user(
    name,
    age,
    gender,
    location,
    condition,
    income_range,
    insurance_level,
    budget_preference,
    blood_group="",
    allergies="",
    medical_conditions="",
    emergency_contact_name="",
    emergency_contact_phone="",
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO User (
            name,
            age,
            gender,
            location,
            condition,
            income_range,
            insurance_level,
            budget_preference,
            blood_group,
            allergies,
            medical_conditions,
            emergency_contact_name,
            emergency_contact_phone
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            age,
            gender,
            location,
            condition,
            income_range,
            insurance_level,
            budget_preference,
            blood_group,
            allergies,
            medical_conditions,
            emergency_contact_name,
            emergency_contact_phone,
        ),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM User WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


# Hospital and doctor model operations

def list_hospitals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Hospital")
    hospitals = cursor.fetchall()
    conn.close()
    return hospitals


def list_emergency_hospitals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM Hospital
        WHERE COALESCE(emergency_capable, 0) = 1
        """
    )
    hospitals = cursor.fetchall()
    conn.close()
    return hospitals


def get_hospital(hospital_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Hospital WHERE id = ?", (hospital_id,))
    hospital = cursor.fetchone()
    conn.close()
    return hospital


def get_doctors_by_hospital(hospital_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Doctor WHERE hospital_id = ? ORDER BY rating DESC, experience_years DESC",
        (hospital_id,),
    )
    doctors = cursor.fetchall()
    conn.close()
    return doctors


def get_doctors_for_specialization(specialization):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Doctor WHERE LOWER(specialization) = LOWER(?)",
        (specialization,),
    )
    doctors = cursor.fetchall()
    conn.close()
    return doctors


# Medicine model operations

def add_medicine(user_id, name, dosage, schedule, total_count):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Medicine (user_id, name, dosage, schedule, taken_count, total_count)
        VALUES (?, ?, ?, ?, 0, ?)
        """,
        (user_id, name, dosage, schedule, total_count),
    )
    conn.commit()
    conn.close()


def get_user_medicines(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Medicine WHERE user_id = ?", (user_id,))
    medicines = cursor.fetchall()
    conn.close()
    return medicines


def increment_medicine_taken(medicine_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE Medicine
        SET taken_count = CASE
            WHEN taken_count < total_count THEN taken_count + 1
            ELSE taken_count
        END
        WHERE id = ?
        """,
        (medicine_id,),
    )
    conn.commit()
    conn.close()


# Health log model operations

def create_health_log(user_id, sleep_hours, stress_level, energy_level, symptoms, date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO HealthLog (user_id, sleep_hours, stress_level, energy_level, symptoms, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, sleep_hours, stress_level, energy_level, symptoms, date),
    )
    conn.commit()
    conn.close()


def get_health_logs(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM HealthLog WHERE user_id = ? ORDER BY date DESC, id DESC",
        (user_id,),
    )
    logs = cursor.fetchall()
    conn.close()
    return logs


def get_latest_health_log(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM HealthLog WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 1",
        (user_id,),
    )
    log = cursor.fetchone()
    conn.close()
    return log


# CareBridge model operations

def list_doctors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Doctor ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Doctor WHERE id = ?", (doctor_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def add_family_member(user_id, name, relationship, contact):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO FamilyMember (user_id, name, relationship, contact)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, name, relationship, contact),
    )
    conn.commit()
    conn.close()


def get_family_members(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM FamilyMember WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def link_patient_doctor(user_id, doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM PatientDoctorLink WHERE user_id = ? AND doctor_id = ?",
        (user_id, doctor_id),
    )
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(
            """
            INSERT INTO PatientDoctorLink (user_id, doctor_id)
            VALUES (?, ?)
            """,
            (user_id, doctor_id),
        )
        conn.commit()
    conn.close()


def get_linked_patients_for_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.*
        FROM PatientDoctorLink pdl
        JOIN User u ON u.id = pdl.user_id
        WHERE pdl.doctor_id = ?
        ORDER BY u.id DESC
        """,
        (doctor_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_linked_doctors_for_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT d.*
        FROM PatientDoctorLink pdl
        JOIN Doctor d ON d.id = pdl.doctor_id
        WHERE pdl.user_id = ?
        ORDER BY d.name ASC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def create_questionnaire(doctor_id, title, created_at):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Questionnaire (doctor_id, title, created_at)
        VALUES (?, ?, ?)
        """,
        (doctor_id, title, created_at),
    )
    conn.commit()
    questionnaire_id = cursor.lastrowid
    conn.close()
    return questionnaire_id


def add_question(questionnaire_id, question_text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Question (questionnaire_id, question_text)
        VALUES (?, ?)
        """,
        (questionnaire_id, question_text),
    )
    conn.commit()
    conn.close()


def get_questionnaire(questionnaire_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Questionnaire WHERE id = ?", (questionnaire_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_questionnaires_for_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT q.*
        FROM Questionnaire q
        JOIN PatientDoctorLink pdl ON pdl.doctor_id = q.doctor_id
        WHERE pdl.user_id = ?
        ORDER BY q.created_at DESC, q.id DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_questions_for_questionnaire(questionnaire_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Question WHERE questionnaire_id = ? ORDER BY id ASC",
        (questionnaire_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_answer(question_id, user_id, answer_text, timestamp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Answer (question_id, user_id, answer_text, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (question_id, user_id, answer_text, timestamp),
    )
    conn.commit()
    conn.close()


def get_answers_for_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.*, q.question_text, q.questionnaire_id
        FROM Answer a
        JOIN Question q ON q.id = a.question_id
        WHERE a.user_id = ?
        ORDER BY a.timestamp DESC, a.id DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_answer_map_for_questionnaire_user(questionnaire_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.*, q.question_text, q.id AS q_id
        FROM Answer a
        JOIN Question q ON q.id = a.question_id
        WHERE q.questionnaire_id = ? AND a.user_id = ?
        ORDER BY a.timestamp DESC
        """,
        (questionnaire_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()

    answer_map = {}
    for row in rows:
        q_id = row["q_id"]
        if q_id not in answer_map:
            answer_map[q_id] = row
    return answer_map


def get_questionnaires_by_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Questionnaire WHERE doctor_id = ? ORDER BY created_at DESC, id DESC",
        (doctor_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
