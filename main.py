from utils.ssl_patch import apply as _apply_ssl_patch
_apply_ssl_patch()
import os
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from agents.input_parser    import input_parser_agent
from agents.flight_agent    import flight_agent
from agents.enrichment_agent import enrichment_agent
from agents.hotel_agent     import hotel_agent
from agents.itinerary_agent import itinerary_agent
from agents.final_agent     import final_agent
from memory.checkpointer    import get_checkpointer


# ── State ─────────────────────────────────────────────────────────────────────

class TravelState(TypedDict):
    # conversation
    messages:               Annotated[list, add_messages]
    user_input:             str

    # parsed travel intent
    origin:                 str
    origin_iata:            str
    destination:            str
    destination_iata:       str
    dest_country:           str
    dest_currency:          str
    depart_date:            str
    return_date:            str
    adults:                 int
    travel_class:           int
    budget_inr:             float
    trip_type:              str
    preferences:            str

    # clarification
    needs_clarification:    bool
    clarification_question: str

    # agent outputs
    flight_results:         dict
    flight_summary:         str
    weather_data:           dict
    weather_summary:        str
    country_info:           dict
    country_summary:        str
    currency_info:          dict
    currency_summary:       str
    hotel_results:          dict
    hotel_summary:          str
    itinerary:              str
    map_html:               str
    final_plan:             str
    final_summary:          str
    error:                  str


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_parsing(state: TravelState) -> str:
    """After input_parser: ask for clarification or proceed to flight search."""
    if state.get("needs_clarification"):
        return "ask_user"
    return "flight_search"


def ask_user_node(state: TravelState) -> dict:
    """Returns clarification question as an AI message and stops the graph."""
    question = state.get("clarification_question", "Could you provide more details about your trip?")
    return {
        "messages": [AIMessage(content=question)],
        "final_summary": question,
    }


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(TravelState)

    # nodes
    graph.add_node("input_parser",  input_parser_agent)
    graph.add_node("ask_user",      ask_user_node)
    graph.add_node("flight_search", flight_agent)
    graph.add_node("enrichment",    enrichment_agent)
    graph.add_node("hotel_search",  hotel_agent)
    graph.add_node("itinerary",     itinerary_agent)
    graph.add_node("final",         final_agent)

    # edges
    graph.add_edge(START, "input_parser")

    graph.add_conditional_edges(
        "input_parser",
        route_after_parsing,
        {
            "ask_user":     "ask_user",
            "flight_search": "flight_search",
        }
    )

    graph.add_edge("ask_user",      END)
    graph.add_edge("flight_search", "enrichment")
    graph.add_edge("enrichment",    "hotel_search")
    graph.add_edge("hotel_search",  "itinerary")
    graph.add_edge("itinerary",     "final")
    graph.add_edge("final",         END)

    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)


# ── Runner ────────────────────────────────────────────────────────────────────

app = build_graph()


def run_travel_agent(user_message: str, thread_id: str = "default") -> dict:
    """
    Run the travel agent with a user message.

    Args:
        user_message: natural language travel request
        thread_id:    unique session ID for memory (one per user)

    Returns:
        dict with final_plan, final_summary, map_html, flight_results,
              hotel_results, itinerary, needs_clarification
    """
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_input": user_message,
        "messages":   [HumanMessage(content=user_message)],
    }

    result = app.invoke(initial_state, config=config)

    return {
        "final_plan":           result.get("final_plan", ""),
        "final_summary":        result.get("final_summary", ""),
        "itinerary":            result.get("itinerary", ""),
        "map_html":             result.get("map_html", ""),
        "flight_results":       result.get("flight_results", {}),
        "hotel_results":        result.get("hotel_results", {}),
        "weather_data":         result.get("weather_data", {}),
        "country_info":         result.get("country_info", {}),
        "currency_info":        result.get("currency_info", {}),
        "needs_clarification":  result.get("needs_clarification", False),
        "clarification_question": result.get("clarification_question", ""),
        "error":                result.get("error", ""),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("\n" + "="*60)
    print("   AI Travel Booking Agent")
    print("   Type your trip request. Type 'quit' to exit.")
    print("="*60 + "\n")

    thread_id = "cli_session_001"

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("\nAgent is thinking...\n")

        result = run_travel_agent(user_input, thread_id=thread_id)

        # if agent needs clarification
        if result.get("needs_clarification"):
            print(f"Agent: {result['clarification_question']}\n")
            continue

        # print flights
        flights = result.get("flight_results", {})
        best    = flights.get("best_flights", [])
        if best:
            print("-" * 60)
            print("FLIGHTS")
            print("-" * 60)
            for i, f in enumerate(best[:3], 1):
                stops = "Non-stop" if f["stops"] == 0 else f"{f['stops']} stop(s)"
                hrs   = f["duration_minutes"] // 60
                mins  = f["duration_minutes"] % 60
                print(f"  {i}. {f['airline']} | {stops} | {hrs}h {mins}m | "
                      f"Dep {f['departure_time']} → Arr {f['arrival_time']} | "
                      f"INR {f['price']:,}")

        # print hotels
        hotels = result.get("hotel_results", {}).get("hotels", [])
        if hotels:
            print("\n" + "-" * 60)
            print("HOTELS")
            print("-" * 60)
            for i, h in enumerate(hotels[:3], 1):
                print(f"  {i}. {h['name']} | {h['stars']} | "
                      f"Rating {h['rating']}/5 | "
                      f"{h['price_per_night']}/night | Total {h['total_price']}")

        # print country + currency snapshot
        country = result.get("country_info", {}).get("data", {})
        currency = result.get("currency_info", {})
        if country or currency:
            print("\n" + "-" * 60)
            print("DESTINATION SNAPSHOT")
            print("-" * 60)
            if country:
                print(f"  Visa       : {country.get('visa_required', 'N/A')}")
                print(f"  Language   : {', '.join(country.get('languages', []))}")
                print(f"  Driving    : {country.get('driving_side', 'N/A').capitalize()}")
            if currency and currency.get("rate"):
                print(f"  Rate       : 1 INR = {currency['rate']} {currency.get('to_currency', '')}")

        # print itinerary
        itinerary = result.get("itinerary", "")
        if itinerary:
            print("\n" + "-" * 60)
            print("ITINERARY")
            print("-" * 60)
            print(itinerary)

        print("\n" + "="*60 + "\n")
