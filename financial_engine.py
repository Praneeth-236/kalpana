def calculate_financial_compatibility(user_budget, hospital_cost):
    """
    Returns a normalized financial score between 0 and 1.

    If hospital cost is within user budget, score is 1.
    If it exceeds budget, score is user_budget / hospital_cost.
    """
    if hospital_cost <= 0:
        return 1.0

    if hospital_cost <= user_budget:
        return 1.0

    return max(0.0, min(1.0, user_budget / hospital_cost))
