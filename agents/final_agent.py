import os
import httpx
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    http_client=httpx.Client(verify=False),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.5,
)

SYSTEM_PROMPT = """You are a friendly travel assistant wrapping up a travel planning session.

Your job is to write a short, warm final message to the user that:
1. Confirms the trip details (route, dates, travellers)
2. Highlights the top flight and hotel picks in 1 line each
3. Gives 2-3 key things to remember (visa, currency, weather)
4. Ends with an encouraging sign-off

Keep it SHORT — max 10 lines. The full itinerary is shown separately, this is just the friendly summary card."""


def final_agent(state: dict) -> dict:
    """
    Generates a short friendly summary message and packages final_plan.
    """
    origin      = state.get("origin", "")
    destination = state.get("destination", "")
    depart_date = state.get("depart_date", "")
    return_date = state.get("return_date", "")
    adults      = state.get("adults", 1)
    itinerary   = state.get("itinerary", "")

    # pick top flight
    flight_results = state.get("flight_results", {})
    best_flights   = flight_results.get("best_flights", []) if isinstance(flight_results, dict) else []
    top_flight     = best_flights[0] if best_flights else None

    # pick top hotel
    hotel_results = state.get("hotel_results", {})
    hotels        = hotel_results.get("hotels", []) if isinstance(hotel_results, dict) else []
    top_hotel     = hotels[0] if hotels else None

    flight_line = (
        f"{top_flight['airline']} — {top_flight['price']} INR, "
        f"{'Non-stop' if top_flight['stops'] == 0 else str(top_flight['stops']) + ' stop(s)'}"
    ) if top_flight else "See flight options above."

    hotel_line = (
        f"{top_hotel['name']} — {top_hotel['price_per_night']}/night, "
        f"Rating {top_hotel['rating']}/5"
    ) if top_hotel else "See hotel options above."

    country_info  = state.get("country_info", {})
    country_data  = country_info.get("data", {}) if isinstance(country_info, dict) else {}
    visa_note     = country_data.get("visa_required", "Check visa requirements.")
    flag          = country_data.get("flag_emoji", "")

    context = f"""
Trip: {origin} → {destination} {flag}
Dates: {depart_date} to {return_date} ({adults} traveller(s))
Top Flight: {flight_line}
Top Hotel: {hotel_line}
Visa: {visa_note}
"""

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ])

    final_summary = response.content

    # package full plan = summary card + full itinerary
    final_plan = f"{final_summary}\n\n---\n\n{itinerary}"

    return {
        "final_plan":    final_plan,
        "final_summary": final_summary,
        "messages":      [AIMessage(content=final_summary)],
    }
