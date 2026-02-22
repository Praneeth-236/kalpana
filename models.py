from database import get_connection


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


# User model operations

def create_user(
    name,
    age,
    gender,
    location,
    condition,
    password,
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
            password,
            income_range,
            insurance_level,
            budget_preference,
            blood_group,
            allergies,
            medical_conditions,
            emergency_contact_name,
            emergency_contact_phone
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            age,
            gender,
            location,
            condition,
            password,
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
    user = _row_to_dict(cursor.fetchone())
    conn.close()
    return user


# Hospital and doctor model operations

def list_hospitals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Hospital")
    hospitals = _rows_to_dicts(cursor.fetchall())
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
    hospitals = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return hospitals


def get_hospital(hospital_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Hospital WHERE id = ?", (hospital_id,))
    hospital = _row_to_dict(cursor.fetchone())
    conn.close()
    return hospital


def get_doctors_by_hospital(hospital_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Doctor WHERE hospital_id = ? ORDER BY rating DESC, experience_years DESC",
        (hospital_id,),
    )
    doctors = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return doctors


def get_doctors_for_specialization(specialization):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Doctor WHERE LOWER(specialization) = LOWER(?)",
        (specialization,),
    )
    doctors = _rows_to_dicts(cursor.fetchall())
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
    medicines = _rows_to_dicts(cursor.fetchall())
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
    logs = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return logs


def get_latest_health_log(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM HealthLog WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 1",
        (user_id,),
    )
    log = _row_to_dict(cursor.fetchone())
    conn.close()
    return log


# CareBridge model operations

def list_doctors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Doctor ORDER BY name ASC")
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def get_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Doctor WHERE id = ?", (doctor_id,))
    row = _row_to_dict(cursor.fetchone())
    conn.close()
    return row


def get_doctor_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM Doctor
        WHERE LOWER(email) = LOWER(?) AND COALESCE(is_portal_doctor, 0) = 1
        """,
        (email,),
    )
    row = _row_to_dict(cursor.fetchone())
    conn.close()
    return row


def get_portal_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM Doctor
        WHERE id = ? AND COALESCE(is_portal_doctor, 0) = 1
        """,
        (doctor_id,),
    )
    row = _row_to_dict(cursor.fetchone())
    conn.close()
    return row


def create_doctor_account(name, email, password, specialization, hospital, created_at):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Doctor (
            name,
            hospital_id,
            specialization,
            experience_years,
            rating,
            contact,
            email,
            password,
            hospital,
            created_at,
            is_portal_doctor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            -1,
            specialization,
            0,
            0,
            email,
            email,
            password,
            hospital,
            created_at,
            1,
        ),
    )
    conn.commit()
    doctor_id = cursor.lastrowid
    conn.close()
    return doctor_id


def connect_patient_to_doctor(doctor_id, patient_id, created_at):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, status
        FROM DoctorPatientLink
        WHERE doctor_id = ? AND patient_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (doctor_id, patient_id),
    )
    existing = _row_to_dict(cursor.fetchone())
    if existing:
        conn.close()
        return existing["id"]

    cursor.execute(
        """
        INSERT INTO DoctorPatientLink (doctor_id, patient_id, status, created_at)
        VALUES (?, ?, 'pending', ?)
        """,
        (doctor_id, patient_id, created_at),
    )
    conn.commit()
    link_id = cursor.lastrowid
    conn.close()
    return link_id


def get_pending_links_for_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dpl.*, u.name AS patient_name
        FROM DoctorPatientLink dpl
        JOIN User u ON u.id = dpl.patient_id
        WHERE dpl.doctor_id = ? AND dpl.status = 'pending'
        ORDER BY dpl.created_at DESC, dpl.id DESC
        """,
        (doctor_id,),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def approve_doctor_patient_link(link_id, doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE DoctorPatientLink
        SET status = 'approved'
        WHERE id = ? AND doctor_id = ?
        """,
        (link_id, doctor_id),
    )
    conn.commit()
    conn.close()


def get_approved_patients_for_doctor(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            u.id AS patient_id,
            u.name,
            ps.risk_level,
            ps.stress_score,
            ps.energy_score,
            ps.trend,
            ps.last_assessment_at
        FROM DoctorPatientLink dpl
        JOIN User u ON u.id = dpl.patient_id
        LEFT JOIN PatientState ps ON ps.user_id = u.id
        WHERE dpl.doctor_id = ? AND dpl.status = 'approved'
        ORDER BY dpl.created_at DESC, dpl.id DESC
        """,
        (doctor_id,),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def is_doctor_linked_to_patient(doctor_id, patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM DoctorPatientLink
        WHERE doctor_id = ? AND patient_id = ? AND status = 'approved'
        LIMIT 1
        """,
        (doctor_id, patient_id),
    )
    linked = cursor.fetchone() is not None
    conn.close()
    return linked


def get_assessment_history_for_patient(user_id, limit=30):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT question, answer, timestamp
        FROM AssessmentHistory
        WHERE user_id = ?
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def add_doctor_prescription(
    doctor_id,
    patient_id,
    medicine_name,
    dosage,
    frequency,
    instructions,
    start_date,
    created_at,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO DoctorPrescription (
            doctor_id,
            patient_id,
            medicine_name,
            dosage,
            frequency,
            instructions,
            start_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doctor_id,
            patient_id,
            medicine_name,
            dosage,
            frequency,
            instructions,
            start_date,
            created_at,
        ),
    )
    conn.commit()
    conn.close()


def get_patient_prescriptions(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dp.*, d.name AS doctor_name
        FROM DoctorPrescription dp
        LEFT JOIN Doctor d ON d.id = dp.doctor_id
        WHERE dp.patient_id = ?
        ORDER BY dp.created_at DESC, dp.id DESC
        """,
        (patient_id,),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def get_doctor_patient_prescriptions(doctor_id, patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM DoctorPrescription
        WHERE doctor_id = ? AND patient_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (doctor_id, patient_id),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


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
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def link_patient_doctor(user_id, doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM PatientDoctorLink WHERE user_id = ? AND doctor_id = ?",
        (user_id, doctor_id),
    )
    exists = _row_to_dict(cursor.fetchone())
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
    rows = _rows_to_dicts(cursor.fetchall())
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
    rows = _rows_to_dicts(cursor.fetchall())
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
    row = _row_to_dict(cursor.fetchone())
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
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def get_questions_for_questionnaire(questionnaire_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Question WHERE questionnaire_id = ? ORDER BY id ASC",
        (questionnaire_id,),
    )
    rows = _rows_to_dicts(cursor.fetchall())
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
    rows = _rows_to_dicts(cursor.fetchall())
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
    rows = _rows_to_dicts(cursor.fetchall())
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
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


# Adaptive assessment model operations

def get_patient_state_row(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PatientState WHERE user_id = ?", (user_id,))
    row = _row_to_dict(cursor.fetchone())
    conn.close()
    return row


def upsert_patient_state(
    user_id,
    stress_score,
    energy_score,
    trend,
    last_updated,
    last_assessment_at=None,
    next_assessment_due=None,
    risk_level=None,
    risk_probability=None,
    risk_reason=None,
    recommendation=None,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO PatientState (
            user_id,
            stress_score,
            energy_score,
            trend,
            last_updated,
            last_assessment_at,
            next_assessment_due,
            risk_level,
            risk_probability,
            risk_reason,
            recommendation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            stress_score = excluded.stress_score,
            energy_score = excluded.energy_score,
            trend = excluded.trend,
            last_updated = excluded.last_updated,
            last_assessment_at = excluded.last_assessment_at,
            next_assessment_due = excluded.next_assessment_due,
            risk_level = excluded.risk_level,
            risk_probability = excluded.risk_probability,
            risk_reason = excluded.risk_reason,
            recommendation = excluded.recommendation
        """,
        (
            user_id,
            stress_score,
            energy_score,
            trend,
            last_updated,
            last_assessment_at,
            next_assessment_due,
            risk_level,
            risk_probability,
            risk_reason,
            recommendation,
        ),
    )
    conn.commit()
    conn.close()


def list_question_bank(condition=None, category=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM QuestionBank WHERE 1=1"
    params = []

    if condition:
        query += " AND LOWER(condition) = LOWER(?)"
        params.append(condition)
    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)

    query += " ORDER BY weight DESC, id ASC"
    cursor.execute(query, tuple(params))
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def get_question_bank_item(question_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM QuestionBank WHERE id = ?", (question_id,))
    row = _row_to_dict(cursor.fetchone())
    conn.close()
    return row


def save_patient_answer(user_id, question_id, answer_value, timestamp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO PatientAnswer (user_id, question_id, answer_value, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, question_id, answer_value, timestamp),
    )
    conn.commit()
    conn.close()


def get_recent_patient_answers(user_id, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT pa.*, qb.category, qb.weight, qb.condition
        FROM PatientAnswer pa
        JOIN QuestionBank qb ON qb.id = pa.question_id
        WHERE pa.user_id = ?
        ORDER BY pa.timestamp DESC, pa.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


def add_assessment_history(user_id, question, answer):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO AssessmentHistory (user_id, question, answer)
        VALUES (?, ?, ?)
        """,
        (user_id, question, answer),
    )
    conn.commit()
    conn.close()


def get_assessment_history_questions(user_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT question
        FROM AssessmentHistory
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return [row["question"] for row in rows]


def get_assessment_history_entries(user_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT question, answer, timestamp
        FROM AssessmentHistory
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return [
        f"Q: {row['question']} | A: {row['answer']} | At: {row['timestamp']}"
        for row in rows
    ]
