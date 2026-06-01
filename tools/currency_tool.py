import os
import requests
from dotenv import load_dotenv

load_dotenv()

EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")
BASE_URL = "https://v6.exchangerate-api.com/v6"


def get_exchange_rate(from_currency: str, to_currency: str, amount: float = 1.0) -> dict:
    """
    Get exchange rate between two currencies.

    Args:
        from_currency: source currency code e.g. "INR"
        to_currency:   target currency code e.g. "JPY"
        amount:        amount to convert (default 1.0)

    Returns:
        dict with rate, converted amount, and useful travel denominations
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/{EXCHANGERATE_API_KEY}/pair/{from_currency.upper()}/{to_currency.upper()}/{amount}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("result") != "success":
            return {"error": data.get("error-type", "Unknown error"), "rate": None}

        rate            = data.get("conversion_rate", 0)
        converted       = data.get("conversion_result", 0)
        last_updated    = data.get("time_last_update_utc", "")

        # useful travel amounts
        denominations = _travel_denominations(rate, from_currency, to_currency)

        return {
            "from_currency":  from_currency.upper(),
            "to_currency":    to_currency.upper(),
            "rate":           rate,
            "amount":         amount,
            "converted":      round(converted, 2),
            "last_updated":   last_updated,
            "denominations":  denominations,
            "error":          None,
        }

    except Exception as e:
        return {"error": str(e), "rate": None}


def _travel_denominations(rate: float, from_cur: str, to_cur: str) -> list:
    """Shows common travel spend amounts converted."""
    amounts = [500, 1000, 5000, 10000, 50000]
    return [
        {
            "from": f"{from_cur} {amt:,}",
            "to":   f"{to_cur} {round(amt * rate, 2):,}"
        }
        for amt in amounts
    ]


def get_travel_budget_breakdown(
    total_budget_inr: float,
    to_currency: str,
    days: int,
    adults: int,
) -> dict:
    """
    Break down a travel budget into per-day, per-person amounts.

    Args:
        total_budget_inr: total trip budget in INR
        to_currency:      destination currency code
        days:             number of travel days
        adults:           number of travellers

    Returns:
        dict with budget breakdown
    """
    rate_data = get_exchange_rate("INR", to_currency, total_budget_inr)

    if rate_data.get("error"):
        return {"error": rate_data["error"]}

    total_dest      = rate_data["converted"]
    per_day         = round(total_dest / days, 2) if days > 0 else 0
    per_person_day  = round(per_day / adults, 2) if adults > 0 else 0

    return {
        "total_inr":        f"INR {total_budget_inr:,.0f}",
        "total_dest":       f"{to_currency} {total_dest:,}",
        "per_day":          f"{to_currency} {per_day:,}",
        "per_person_day":   f"{to_currency} {per_person_day:,}",
        "days":             days,
        "adults":           adults,
        "rate":             rate_data["rate"],
        "error":            None,
    }


def format_currency_for_llm(currency_data: dict) -> str:
    """Converts currency data into a readable string for the LLM."""
    if currency_data.get("error"):
        return f"Currency fetch failed: {currency_data['error']}"

    lines = [
        f"=== CURRENCY: {currency_data['from_currency']} → {currency_data['to_currency']} ===",
        f"Exchange Rate : 1 {currency_data['from_currency']} = {currency_data['rate']} {currency_data['to_currency']}",
        f"Last Updated  : {currency_data.get('last_updated', 'N/A')}",
        "",
        "Quick Reference:",
    ]

    for d in currency_data.get("denominations", []):
        lines.append(f"  {d['from']} = {d['to']}")

    return "\n".join(lines)
