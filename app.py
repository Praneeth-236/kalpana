import os
from datetime import datetime

from flask import Flask, abort, redirect, render_template, send_file, request, session, url_for
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from adherence_tracker import add_medicine, calculate_adherence_score, log_medicine_taken
from adaptive_question_engine import (
    get_fallback_questions,
    get_adaptive_questions,
    get_patient_state,
    is_assessment_due,
    select_adaptive_questions,
    update_patient_state,
)
from carebridge_engine import calculate_patient_risk, generate_doctor_recommendation
from config import BASE_URL
from database import init_db
from emergency_engine import recommend_emergency_hospital
from explanation_engine import (
    generate_doctor_recommendation_explanation,
    generate_hospital_explanation,
)
from geolocation_service import geocode_location
from health_monitor import compute_health_stability
from health_summary_engine import generate_patient_summary
from hospital_service import fetch_nearest_hospitals_overpass
from models import (
    add_doctor_prescription,
    approve_doctor_patient_link,
    add_question,
    connect_patient_to_doctor,
    create_doctor_account,
    create_questionnaire,
    create_user,
    get_approved_patients_for_doctor,
    get_assessment_history_for_patient,
    get_doctor_patient_prescriptions,
    get_answer_map_for_questionnaire_user,
    get_doctor,
    get_doctor_by_email,
    get_doctors_by_hospital,
    get_emergency_contacts,
    get_health_logs,
    get_health_summary,
    get_hospital,
    get_prescriptions,
    get_linked_patients_for_doctor,
    get_latest_health_log,
    get_questionnaire,
    get_questionnaires_by_doctor,
    get_questionnaires_for_user,
    get_questions_for_questionnaire,
    get_user,
    get_user_medicines,
    get_patient_state_row,
    get_pending_links_for_doctor,
    get_patient_prescriptions,
    get_portal_doctor,
    is_doctor_linked_to_patient,
    link_patient_doctor,
    list_hospitals,
    save_answer,
)
from qr_generator import generate_qr
from scoring_engine import rank_hospitals_with_location

app = Flask(__name__)
CORS(app)
app.secret_key = "carematch-hackathon-secret"


def _is_patient_session():
    return session.get("role") == "patient" and session.get("user_id") is not None


def _is_doctor_session():
    return session.get("role") == "doctor" and session.get("doctor_id") is not None


def _is_local_url(value):
    normalized = (value or "").lower()
    return "127.0.0.1" in normalized or "localhost" in normalized


def _resolve_qr_base_url(request_host_url):
    # Priority:
    # 1) Public BASE_URL from config/env/deployment
    # 2) Public request host (when app is accessed via tunnel/domain)
    # 3) Local fallback
    if not _is_local_url(BASE_URL):
        return BASE_URL
    if not _is_local_url(request_host_url):
        return request_host_url
    return BASE_URL


@app.before_request
def setup_database_once():
    init_db()


def _get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user(user_id)


def _get_current_doctor():
    doctor_id = session.get("doctor_id")
    if not doctor_id:
        return None
    return get_portal_doctor(doctor_id)


def _to_float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rank_for_user(user, user_lat=None, user_lon=None):
    if user_lat is None or user_lon is None:
        user_location_coords = geocode_location(user.get("location"))
        if user_location_coords:
            user_lat, user_lon = user_location_coords

    use_overpass = user_lat is not None and user_lon is not None

    hospitals = []
    doctors_by_hospital = {}
    hospital_coords_by_id = {}
    overpass_used = False

    if use_overpass:
        overpass_used = True
        hospitals = fetch_nearest_hospitals_overpass(
            user_lat,
            user_lon,
            preferred_condition=user.get("condition"),
        )
        for hospital in hospitals:
            hospital_coords_by_id[hospital["id"]] = (
                hospital["latitude"],
                hospital["longitude"],
            )

    if not hospitals:
        return [], overpass_used

    ranked = rank_hospitals_with_location(
        user,
        hospitals,
        doctors_by_hospital,
        user_lat=user_lat,
        user_lon=user_lon,
        hospital_coords_by_id=hospital_coords_by_id,
    )
    for item in ranked:
        item["explanation"] = generate_hospital_explanation(item)
    return ranked, overpass_used


@app.route("/")
def landing_page():
    return render_template("index.html")


@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():
    message = None

    if request.method == "POST":
        user_id_text = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        if not user_id_text.isdigit():
            message = "Enter a valid Patient ID."
        elif not password:
            message = "Password is required."
        else:
            user = get_user(int(user_id_text))
            if not user:
                message = "Patient not found. Create your profile first."
            elif not user.get("password"):
                message = "This profile has no password set. Create a new profile with password."
            elif not check_password_hash(user["password"], password):
                message = "Invalid Patient ID or password."
            else:
                session.pop("doctor_id", None)
                session["user_id"] = user["id"]
                session["role"] = "patient"
                return redirect(url_for("patient_dashboard"))

    return render_template("patient_login.html", message=message)


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        raw_password = request.form.get("password", "")
        if len(raw_password) < 6:
            return render_template(
                "hospital_search.html",
                message="Create a patient password with at least 6 characters.",
            )

        user_id = create_user(
            name=request.form.get("name", "Anonymous User").strip() or "Anonymous User",
            age=int(request.form.get("age", 30)),
            gender=request.form.get("gender", "Not specified"),
            location=request.form.get("location", "Bengaluru"),
            condition=request.form.get("condition", "general").lower(),
            password=generate_password_hash(raw_password),
            income_range=request.form.get("income_range", "Medium"),
            insurance_level=request.form.get("insurance_level", "Basic"),
            budget_preference=float(request.form.get("budget_preference", 3000)),
            blood_group=request.form.get("blood_group", "").strip(),
            allergies=request.form.get("allergies", "").strip(),
            medical_conditions=request.form.get("medical_conditions", "").strip(),
            emergency_contact_name=request.form.get("emergency_contact_name", "").strip(),
            emergency_contact_phone=request.form.get("emergency_contact_phone", "").strip(),
        )
        session["user_id"] = user_id
        session["role"] = "patient"
        session["new_patient_id_notice"] = user_id
        return redirect(url_for("results"))

    return render_template("hospital_search.html", message=None)


@app.route("/results")
def results():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    return redirect(url_for("hospitals_page", lat=lat, lon=lon))


@app.route("/hospitals")
def hospitals_page():
    user = _get_current_user()
    if not user:
        return redirect(url_for("search"))

    user_lat = _to_float_or_none(request.args.get("lat"))
    user_lon = _to_float_or_none(request.args.get("lon"))

    ranked_hospitals, overpass_used = _rank_for_user(user, user_lat=user_lat, user_lon=user_lon)
    best_hospital = ranked_hospitals[0] if ranked_hospitals else None
    new_patient_id_notice = session.pop("new_patient_id_notice", None)
    return render_template(
        "hospitals.html",
        user=user,
        ranked_hospitals=ranked_hospitals,
        best_hospital=best_hospital,
        user_lat=user_lat,
        user_lon=user_lon,
        new_patient_id_notice=new_patient_id_notice,
        overpass_used=overpass_used,
    )


@app.route("/doctor/register", methods=["GET", "POST"])
def doctor_register():
    message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        specialization = request.form.get("specialization", "General").strip()
        hospital = request.form.get("hospital", "Independent").strip()

        if not name or not email or not password:
            message = "Name, email, and password are required."
        elif get_doctor_by_email(email):
            message = "Doctor with this email already exists."
        else:
            password_hash = generate_password_hash(password)
            create_doctor_account(
                name=name,
                email=email,
                password=password_hash,
                specialization=specialization,
                hospital=hospital,
                created_at=datetime.now().isoformat(timespec="seconds"),
            )
            return redirect(url_for("doctor_login"))

    return render_template("doctor_register.html", message=message)


@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    message = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        doctor = get_doctor_by_email(email)
        if not doctor or not doctor["password"]:
            message = "Invalid email or password."
        elif not check_password_hash(doctor["password"], password):
            message = "Invalid email or password."
        else:
            session.pop("user_id", None)
            session["doctor_id"] = doctor["id"]
            session["role"] = "doctor"
            return redirect(url_for("doctor_portal_dashboard"))

    return render_template("doctor_login.html", message=message)


@app.route("/doctor/dashboard")
def doctor_portal_dashboard():
    if not _is_doctor_session():
        return redirect(url_for("doctor_login"))

    doctor = _get_current_doctor()
    if not doctor:
        return redirect(url_for("doctor_login"))

    linked_patients = get_approved_patients_for_doctor(doctor["id"])
    pending_links = get_pending_links_for_doctor(doctor["id"])

    patient_rows = []
    for patient in linked_patients:
        patient_rows.append(
            {
                "patient": patient,
                "summary": generate_patient_summary(patient["patient_id"]),
            }
        )

    return render_template(
        "doctor_dashboard.html",
        portal_mode=True,
        doctor=doctor,
        patient_rows=patient_rows,
        pending_links=pending_links,
    )


@app.route("/connect_doctor", methods=["GET", "POST"])
def connect_doctor():
    user = _get_current_user()
    if not user:
        return redirect(url_for("search"))

    message = None
    if request.method == "POST":
        doctor_email = request.form.get("doctor_email", "").strip().lower()
        doctor = get_doctor_by_email(doctor_email)
        if not doctor:
            message = "Doctor not found for this email."
        else:
            connect_patient_to_doctor(
                doctor_id=doctor["id"],
                patient_id=user["id"],
                created_at=datetime.now().isoformat(timespec="seconds"),
            )
            message = "Connection request sent to doctor (pending approval)."

    return render_template("connect_doctor.html", user=user, message=message)


@app.route("/doctor/approve_patient/<int:link_id>")
def doctor_approve_patient(link_id):
    doctor = _get_current_doctor()
    if not doctor:
        return redirect(url_for("doctor_login"))

    approve_doctor_patient_link(link_id, doctor["id"])
    return redirect(url_for("doctor_portal_dashboard"))


@app.route("/doctor/patient/<int:patient_id>")
def doctor_patient_detail(patient_id):
    doctor = _get_current_doctor()
    if not doctor:
        return redirect(url_for("doctor_login"))

    if not is_doctor_linked_to_patient(doctor["id"], patient_id):
        abort(403)

    patient = get_user(patient_id)
    patient_state = get_patient_state_row(patient_id)
    assessment_history = get_assessment_history_for_patient(patient_id, limit=30)
    prescriptions = get_doctor_patient_prescriptions(doctor["id"], patient_id)
    adherence = calculate_adherence_score(patient_id)
    patient_health_summary = generate_patient_summary(patient_id)

    return render_template(
        "doctor_patient.html",
        doctor=doctor,
        patient=patient,
        patient_state=patient_state,
        assessment_history=assessment_history,
        prescriptions=prescriptions,
        adherence=adherence,
        patient_health_summary=patient_health_summary,
    )


@app.route("/doctor/add_prescription/<int:patient_id>", methods=["GET", "POST"])
def doctor_add_prescription(patient_id):
    doctor = _get_current_doctor()
    if not doctor:
        return redirect(url_for("doctor_login"))

    if not is_doctor_linked_to_patient(doctor["id"], patient_id):
        abort(403)

    patient = get_user(patient_id)
    if not patient:
        abort(404)

    message = None
    if request.method == "POST":
        medicine_name = request.form.get("medicine_name", "").strip()
        dosage = request.form.get("dosage", "").strip()
        frequency = request.form.get("frequency", "").strip()
        instructions = request.form.get("instructions", "").strip()
        start_date = request.form.get("start_date", "").strip()

        if medicine_name and dosage and frequency and start_date:
            add_doctor_prescription(
                doctor_id=doctor["id"],
                patient_id=patient_id,
                medicine_name=medicine_name,
                dosage=dosage,
                frequency=frequency,
                instructions=instructions,
                start_date=start_date,
                created_at=datetime.now().isoformat(timespec="seconds"),
            )
            return redirect(url_for("doctor_patient_detail", patient_id=patient_id))

        message = "Please fill all required fields."

    return render_template(
        "doctor_add_prescription.html",
        doctor=doctor,
        patient=patient,
        message=message,
    )


@app.route("/doctors/<int:hospital_id>")
def doctors(hospital_id):
    hospital = get_hospital(hospital_id)
    if not hospital:
        return redirect(url_for("results"))

    doctors_list = get_doctors_by_hospital(hospital_id)
    ranked_doctors = sorted(
        doctors_list,
        key=lambda d: (d["rating"], d["experience_years"]),
        reverse=True,
    )

    return render_template(
        "doctor_results.html",
        hospital=hospital,
        doctors=ranked_doctors,
    )


@app.route("/medicines", methods=["GET", "POST"])
def medicines():
    user = _get_current_user()
    if not user:
        return redirect(url_for("search"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            add_medicine(
                user_id=user["id"],
                name=request.form.get("name", "").strip(),
                dosage=request.form.get("dosage", "").strip(),
                schedule=request.form.get("schedule", "").strip(),
                total_count=int(request.form.get("total_count", 1)),
            )
        elif action == "taken":
            medicine_id = int(request.form.get("medicine_id"))
            log_medicine_taken(medicine_id)

        return redirect(url_for("medicines"))

    medicines_list = get_user_medicines(user["id"])
    adherence = calculate_adherence_score(user["id"])

    return render_template(
        "medicine_tracker.html",
        user=user,
        medicines=medicines_list,
        adherence=adherence,
    )


@app.route("/dashboard")
def dashboard():
    return redirect(url_for("patient_dashboard"))


@app.route("/patient/dashboard")
def patient_dashboard():
    if not _is_patient_session():
        return redirect(url_for("patient_login"))

    user = _get_current_user()
    if not user:
        return redirect(url_for("patient_login"))

    adherence = calculate_adherence_score(user["id"])
    medicines = get_user_medicines(user["id"])
    prescriptions = get_patient_prescriptions(user["id"])
    health_logs = get_health_logs(user["id"])
    latest_log = get_latest_health_log(user["id"])

    health_summary = None
    if latest_log:
        health_summary = compute_health_stability(
            sleep_hours=latest_log["sleep_hours"],
            stress_level=latest_log["stress_level"],
            energy_level=latest_log["energy_level"],
            adherence_score=adherence["ratio"],
        )

    ranked_hospitals, _ = _rank_for_user(user)
    top_recommendation = ranked_hospitals[0] if ranked_hospitals else None
    adaptive_state = get_patient_state(user["id"])
    patient_health_summary = generate_patient_summary(user["id"])
    adaptive_risk = {
        "risk": adaptive_state.get("risk_level") or calculate_patient_risk(user["id"])["risk"],
        "risk_probability": adaptive_state.get("risk_probability"),
        "risk_reason": adaptive_state.get("risk_reason"),
        "recommendation": adaptive_state.get("recommendation"),
    }

    return render_template(
        "patient_dashboard.html",
        user=user,
        adherence=adherence,
        medicines=medicines,
        prescriptions=prescriptions,
        health_logs=health_logs,
        health_summary=health_summary,
        patient_health_summary=patient_health_summary,
        top_recommendation=top_recommendation,
        adaptive_state=adaptive_state,
        adaptive_risk=adaptive_risk,
    )


@app.route("/patient/logout")
def patient_logout():
    session.pop("user_id", None)
    session.pop("role", None)
    return redirect(url_for("patient_login"))


@app.route("/doctor/logout")
def doctor_logout():
    session.pop("doctor_id", None)
    session.pop("role", None)
    return redirect(url_for("doctor_login"))


@app.route("/emergency/<int:user_id>")
def emergency_profile(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    prescriptions = get_prescriptions(user_id)
    health_summary = get_health_summary(user_id)
    emergency_contacts = get_emergency_contacts(user_id)
    patient_state = health_summary.get("state") or {}

    return render_template(
        "emergency_profile.html",
        user=user,
        prescriptions=prescriptions,
        health_summary=health_summary,
        emergency_contacts=emergency_contacts,
        risk_level=patient_state.get("risk_level") or "Unknown",
    )


@app.route("/call_ambulance/<int:hospital_id>")
def call_ambulance(hospital_id):
    hospital = get_hospital(hospital_id)
    if not hospital:
        abort(404)

    ambulance_number = hospital["ambulance_number"] or "Not Available"
    return render_template(
        "ambulance_call.html",
        hospital=hospital,
        ambulance_number=ambulance_number,
    )


@app.route("/generate_qr/<int:user_id>")
def generate_qr_route(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    qr_base_url = _resolve_qr_base_url(request.host_url)
    file_path = generate_qr(user_id, base_url=qr_base_url)
    return send_file(file_path, mimetype="image/png")


@app.route("/qr/<int:user_id>")
def view_qr(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    from qr_generator import generate_qr as _generate_qr

    qr_base_url = _resolve_qr_base_url(request.host_url)
    filepath = _generate_qr(user_id, base_url=qr_base_url)

    return f'''
    <h2>Emergency QR Code</h2>
    <img src="/{filepath}" width="250">
    <p>Scan this QR from any phone.</p>
    '''


@app.route("/doctor/<int:doctor_id>/dashboard", methods=["GET", "POST"])
def doctor_dashboard(doctor_id):
    doctor = get_doctor(doctor_id)
    if not doctor:
        abort(404)

    if request.method == "POST":
        user_id = int(request.form.get("user_id", 0))
        if user_id > 0 and get_user(user_id):
            link_patient_doctor(user_id, doctor_id)
        return redirect(url_for("doctor_dashboard", doctor_id=doctor_id))

    linked_patients = get_linked_patients_for_doctor(doctor_id)
    patient_cards = []
    for patient in linked_patients:
        risk_snapshot = calculate_patient_risk(patient["id"])
        recommendation = generate_doctor_recommendation(risk_snapshot["risk"])
        explanation = generate_doctor_recommendation_explanation(
            risk_snapshot["risk"], recommendation
        )
        patient_cards.append(
            {
                "patient": patient,
                "adherence_score": risk_snapshot["adherence_score"],
                "health_score": risk_snapshot["health_score"],
                "risk": risk_snapshot["risk"],
                "recommendation": recommendation,
                "recommendation_explanation": explanation,
            }
        )

    return render_template(
        "doctor_dashboard.html",
        portal_mode=False,
        doctor=doctor,
        patient_cards=patient_cards,
    )


@app.route("/doctor/<int:doctor_id>/create_questionnaire", methods=["GET", "POST"])
def doctor_create_questionnaire(doctor_id):
    doctor = get_doctor(doctor_id)
    if not doctor:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "General Health Check").strip()
        question_lines = request.form.get("questions", "").splitlines()
        question_texts = [q.strip() for q in question_lines if q.strip()]

        if title and question_texts:
            questionnaire_id = create_questionnaire(
                doctor_id=doctor_id,
                title=title,
                created_at=datetime.now().isoformat(timespec="seconds"),
            )
            for question_text in question_texts:
                add_question(questionnaire_id, question_text)

            return redirect(url_for("doctor_dashboard", doctor_id=doctor_id))

    return render_template("create_questionnaire.html", doctor=doctor)


@app.route("/doctor/<int:doctor_id>/view_answers/<int:user_id>")
def doctor_view_answers(doctor_id, user_id):
    doctor = get_doctor(doctor_id)
    user = get_user(user_id)
    if not doctor or not user:
        abort(404)

    questionnaires = get_questionnaires_by_doctor(doctor_id)
    questionnaire_views = []
    for questionnaire in questionnaires:
        questions = get_questions_for_questionnaire(questionnaire["id"])
        answer_map = get_answer_map_for_questionnaire_user(questionnaire["id"], user_id)
        questionnaire_views.append(
            {
                "questionnaire": questionnaire,
                "questions": questions,
                "answer_map": answer_map,
            }
        )

    return render_template(
        "view_answers.html",
        doctor=doctor,
        patient=user,
        questionnaire_views=questionnaire_views,
    )


@app.route("/patient/<int:user_id>/questionnaires")
def patient_questionnaires(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    questionnaires = get_questionnaires_for_user(user_id)
    return render_template(
        "patient_questionnaires.html",
        user=user,
        questionnaires=questionnaires,
    )


@app.route("/patient/<int:user_id>/answer/<int:questionnaire_id>", methods=["GET", "POST"])
def patient_answer_questionnaire(user_id, questionnaire_id):
    user = get_user(user_id)
    questionnaire = get_questionnaire(questionnaire_id)
    if not user or not questionnaire:
        abort(404)

    questions = get_questions_for_questionnaire(questionnaire_id)

    if request.method == "POST":
        timestamp = datetime.now().isoformat(timespec="seconds")
        for question in questions:
            field_name = f"q_{question['id']}"
            answer_text = request.form.get(field_name, "").strip()
            if answer_text:
                save_answer(
                    question_id=question["id"],
                    user_id=user_id,
                    answer_text=answer_text,
                    timestamp=timestamp,
                )
        return redirect(url_for("patient_questionnaires", user_id=user_id))

    return render_template(
        "patient_questionnaires.html",
        user=user,
        questionnaires=[],
        questionnaire=questionnaire,
        questions=questions,
    )


@app.route("/family/<int:user_id>/dashboard")
def family_dashboard(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    adherence = calculate_adherence_score(user_id)
    risk_snapshot = calculate_patient_risk(user_id)
    recommendation = generate_doctor_recommendation(risk_snapshot["risk"])
    recommendation_explanation = generate_doctor_recommendation_explanation(
        risk_snapshot["risk"], recommendation
    )
    emergency_hospital = recommend_emergency_hospital(user["location"])

    return render_template(
        "family_dashboard.html",
        user=user,
        adherence=adherence,
        risk_snapshot=risk_snapshot,
        recommendation=recommendation,
        recommendation_explanation=recommendation_explanation,
        emergency_hospital=emergency_hospital,
    )


@app.route("/assessment/<int:user_id>")
def adaptive_assessment(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    state = get_patient_state(user_id)
    due = is_assessment_due(user_id)
    questions_or_message = get_adaptive_questions(user_id)
    if isinstance(questions_or_message, str):
        due_message = questions_or_message
        questions = []
    else:
        due_message = None
        questions = questions_or_message

    if due and not questions:
        questions = [
            {
                "id": f"fallback_{idx}",
                "question_text": question_text,
                "category": "stress",
                "weight": 6,
                "source": "fallback",
            }
            for idx, question_text in enumerate(get_fallback_questions(), start=1)
        ]

    return render_template(
        "adaptive_assessment.html",
        user=user,
        state=state,
        due=due,
        due_message=due_message,
        questions=questions,
        result=None,
    )


@app.route("/submit_assessment/<int:user_id>", methods=["POST"])
def submit_adaptive_assessment(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    if not is_assessment_due(user_id):
        state = get_patient_state(user_id)
        return render_template(
            "adaptive_assessment.html",
            user=user,
            state=state,
            due=False,
            due_message="Next assessment available tomorrow",
            questions=[],
            result=None,
        )

    questions_or_message = get_adaptive_questions(user_id)
    questions = questions_or_message if isinstance(questions_or_message, list) else []
    if not questions:
        questions = [
            {
                "id": f"fallback_{idx}",
                "question_text": question_text,
                "category": "stress",
                "weight": 6,
                "source": "fallback",
            }
            for idx, question_text in enumerate(get_fallback_questions(), start=1)
        ]
    answer_values = request.form.getlist("answers")

    parsed_answers = {}
    question_context = {}
    for question, value in zip(questions, answer_values):
        if value and str(value).strip():
            question_key = str(question["id"])
            parsed_answers[question_key] = int(value)
            question_context[question_key] = {
                "category": question.get("category", "stress"),
                "weight": int(question.get("weight", 6)),
                "question_text": question.get("question_text", "Adaptive assessment question"),
            }

    state = update_patient_state(
        user_id,
        parsed_answers,
        question_context=question_context,
    )

    adherence = calculate_adherence_score(user_id)
    latest_log = get_latest_health_log(user_id)
    health_score = 0.0
    if latest_log:
        health_summary = compute_health_stability(
            sleep_hours=latest_log["sleep_hours"],
            stress_level=latest_log["stress_level"],
            energy_level=latest_log["energy_level"],
            adherence_score=adherence["ratio"],
        )
        health_score = health_summary["health_percentage"]

    risk_snapshot = calculate_patient_risk(user_id)
    recommendation = generate_doctor_recommendation(risk_snapshot["risk"])

    next_due = is_assessment_due(user_id)
    next_questions_or_message = get_adaptive_questions(user_id)
    if isinstance(next_questions_or_message, str):
        next_questions = []
        next_due_message = next_questions_or_message
    else:
        next_questions = next_questions_or_message
        next_due_message = None

    return render_template(
        "adaptive_assessment.html",
        user=user,
        state=state,
        due=next_due,
        due_message=next_due_message,
        questions=next_questions,
        result={
            "health_score": round(health_score, 2),
            "risk_level": risk_snapshot["risk"],
            "recommendation": recommendation,
        },
    )


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
