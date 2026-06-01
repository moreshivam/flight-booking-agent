from tools.hotel_tool import search_hotels, format_hotels_for_llm


def hotel_agent(state: dict) -> dict:
    """
    Searches for hotels at the destination using parsed travel intent from state.
    Writes hotel_results and hotel_summary back to state.
    """
    destination  = state.get("destination", "")
    depart_date  = state.get("depart_date", "")
    return_date  = state.get("return_date", "")
    adults       = state.get("adults", 2)
    budget_inr   = state.get("budget_inr", 0)
    dest_currency = state.get("dest_currency", "USD")

    if not destination or not depart_date or not return_date:
        return {
            "hotel_results":  {},
            "hotel_summary":  "Missing destination or travel dates — cannot search hotels.",
            "error":          "incomplete_input",
        }

    # rough max price per night from budget (40% of daily budget)
    max_price = None
    if budget_inr and budget_inr > 0:
        currency_info = state.get("currency_info", {})
        rate = currency_info.get("rate", 0)
        if rate:
            from_date  = depart_date
            to_date    = return_date
            nights     = _count_nights(from_date, to_date)
            daily_dest = (budget_inr * rate) / max(nights, 1)
            max_price  = int(daily_dest * 0.4)  # 40% of daily budget for hotel

    hotel_data = search_hotels(
        destination  = destination,
        check_in     = depart_date,
        check_out    = return_date,
        adults       = adults,
        currency     = dest_currency,
        max_price    = max_price,
        sort_by      = 3,   # lowest price first
    )

    summary = format_hotels_for_llm(hotel_data)

    return {
        "hotel_results": hotel_data,
        "hotel_summary": summary,
        "error":         hotel_data.get("error"),
    }


def _count_nights(check_in: str, check_out: str) -> int:
    """Calculate number of nights between two YYYY-MM-DD dates."""
    try:
        from datetime import date
        d1 = date.fromisoformat(check_in)
        d2 = date.fromisoformat(check_out)
        return max((d2 - d1).days, 1)
    except Exception:
        return 1
