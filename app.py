from datetime import date, datetime

from flask import Flask, abort, redirect, render_template, send_file, request, session, url_for

from adherence_tracker import add_medicine, calculate_adherence_score, log_medicine_taken
from carebridge_engine import calculate_patient_risk, generate_doctor_recommendation
from database import init_db
from emergency_engine import recommend_emergency_hospital
from explanation_engine import (
    generate_doctor_recommendation_explanation,
    generate_hospital_explanation,
)
from health_monitor import compute_health_stability
from models import (
    add_question,
    create_health_log,
    create_questionnaire,
    create_user,
    get_answer_map_for_questionnaire_user,
    get_doctor,
    get_doctors_by_hospital,
    get_health_logs,
    get_hospital,
    get_linked_patients_for_doctor,
    get_latest_health_log,
    get_questionnaire,
    get_questionnaires_by_doctor,
    get_questionnaires_for_user,
    get_questions_for_questionnaire,
    get_user,
    get_user_medicines,
    link_patient_doctor,
    list_hospitals,
    save_answer,
)
from qr_generator import generate_qr
from scoring_engine import rank_hospitals

app = Flask(__name__)
app.secret_key = "carematch-hackathon-secret"


@app.before_request
def setup_database_once():
    init_db()


def _get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user(user_id)


def _rank_for_user(user):
    hospitals = list_hospitals()
    doctors_by_hospital = {h["id"]: get_doctors_by_hospital(h["id"]) for h in hospitals}
    ranked = rank_hospitals(user, hospitals, doctors_by_hospital)
    for item in ranked:
        item["explanation"] = generate_hospital_explanation(item)
    return ranked


@app.route("/")
def home():
    user = _get_current_user()
    return render_template("home.html", user=user)


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        user_id = create_user(
            name=request.form.get("name", "Anonymous User").strip() or "Anonymous User",
            age=int(request.form.get("age", 30)),
            gender=request.form.get("gender", "Not specified"),
            location=request.form.get("location", "Bengaluru"),
            condition=request.form.get("condition", "general").lower(),
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
        return redirect(url_for("results"))

    return render_template("hospital_search.html")


@app.route("/results")
def results():
    user = _get_current_user()
    if not user:
        return redirect(url_for("search"))

    ranked_hospitals = _rank_for_user(user)
    return render_template(
        "hospital_results.html",
        user=user,
        ranked_hospitals=ranked_hospitals,
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


@app.route("/health_assessment", methods=["GET", "POST"])
def health_assessment():
    user = _get_current_user()
    if not user:
        return redirect(url_for("search"))

    latest_result = None

    if request.method == "POST":
        sleep_hours = float(request.form.get("sleep_hours", 0))
        stress_level = int(request.form.get("stress_level", 5))
        energy_level = int(request.form.get("energy_level", 5))
        symptoms = request.form.get("symptoms", "").strip()

        adherence = calculate_adherence_score(user["id"])
        latest_result = compute_health_stability(
            sleep_hours=sleep_hours,
            stress_level=stress_level,
            energy_level=energy_level,
            adherence_score=adherence["ratio"],
        )

        create_health_log(
            user_id=user["id"],
            sleep_hours=sleep_hours,
            stress_level=stress_level,
            energy_level=energy_level,
            symptoms=symptoms,
            date=str(date.today()),
        )

    return render_template(
        "health_assessment.html",
        user=user,
        latest_result=latest_result,
    )


@app.route("/dashboard")
def dashboard():
    user = _get_current_user()
    if not user:
        return redirect(url_for("search"))

    adherence = calculate_adherence_score(user["id"])
    medicines = get_user_medicines(user["id"])
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

    ranked_hospitals = _rank_for_user(user)
    top_recommendation = ranked_hospitals[0] if ranked_hospitals else None

    return render_template(
        "dashboard.html",
        user=user,
        adherence=adherence,
        medicines=medicines,
        health_logs=health_logs,
        health_summary=health_summary,
        top_recommendation=top_recommendation,
    )


@app.route("/emergency/<int:user_id>")
def emergency_profile(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    best_hospital = recommend_emergency_hospital(user["location"])
    return render_template(
        "emergency_profile.html",
        user=user,
        hospital=best_hospital,
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

    file_path = generate_qr(user_id)
    return send_file(file_path, mimetype="image/png")


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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
