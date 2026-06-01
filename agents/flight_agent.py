from tools.flight_tool import search_flights, format_flights_for_llm


def flight_agent(state: dict) -> dict:
    """
    Searches for flights using parsed travel intent from state.
    Writes flight_results and flight_summary back to state.
    """
    origin_iata      = state.get("origin_iata", "")
    destination_iata = state.get("destination_iata", "")
    depart_date      = state.get("depart_date", "")
    return_date      = state.get("return_date") or None
    adults           = state.get("adults", 1)
    travel_class     = state.get("travel_class", 1)

    # fallback: use city name as IATA if code not resolved
    origin      = origin_iata      or state.get("origin", "")
    destination = destination_iata or state.get("destination", "")

    if not origin or not destination or not depart_date:
        return {
            "flight_results":  {},
            "flight_summary":  "Missing origin, destination or travel date — cannot search flights.",
            "error":           "incomplete_input",
        }

    flight_data = search_flights(
        origin       = origin,
        destination  = destination,
        depart_date  = depart_date,
        return_date  = return_date,
        adults       = adults,
        travel_class = travel_class,
        currency     = "INR",
    )

    summary = format_flights_for_llm(flight_data)

    return {
        "flight_results": flight_data,
        "flight_summary": summary,
        "error":          flight_data.get("error"),
    }
