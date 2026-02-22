from models import add_medicine as add_medicine_record
from models import get_user_medicines, increment_medicine_taken


def add_medicine(user_id, name, dosage, schedule, total_count):
    """Add a medicine for a user with total planned doses."""
    add_medicine_record(user_id, name, dosage, schedule, total_count)


def log_medicine_taken(medicine_id):
    """Mark one dose as taken, capping at total_count."""
    increment_medicine_taken(medicine_id)


def calculate_adherence_score(user_id):
    """
    adherence_score = taken_count / total_count
    Returns percentage and ratio.
    """
    medicines = get_user_medicines(user_id)
    if not medicines:
        return {"ratio": 0.0, "percentage": 0.0, "taken": 0, "total": 0}

    taken = sum(m["taken_count"] for m in medicines)
    total = sum(m["total_count"] for m in medicines)

    ratio = (taken / total) if total > 0 else 0.0
    return {
        "ratio": round(ratio, 4),
        "percentage": round(ratio * 100, 2),
        "taken": taken,
        "total": total,
    }
