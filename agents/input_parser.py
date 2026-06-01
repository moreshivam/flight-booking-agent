import os
import json
import httpx
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    http_client=httpx.Client(verify=False),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

SYSTEM_PROMPT = """You are a travel intent parser. Extract structured travel information from the user's message.

Return a JSON object with EXACTLY these fields:
{
  "origin":           string,   // departure city or airport e.g. "Mumbai" or "BOM"
  "origin_iata":      string,   // IATA airport code e.g. "BOM" (empty string if unknown)
  "destination":      string,   // destination city e.g. "Tokyo"
  "destination_iata": string,   // IATA airport code e.g. "NRT" (empty string if unknown)
  "dest_country":     string,   // destination country e.g. "Japan"
  "dest_currency":    string,   // destination currency code e.g. "JPY"
  "depart_date":      string,   // "YYYY-MM-DD" format (empty string if not given)
  "return_date":      string,   // "YYYY-MM-DD" format (empty string if one-way or not given)
  "adults":           integer,  // number of adult passengers (default 1)
  "travel_class":     integer,  // 1=Economy 2=Premium Economy 3=Business 4=First (default 1)
  "budget_inr":       number,   // total budget in INR (0 if not mentioned)
  "trip_type":        string,   // "round_trip" or "one_way"
  "preferences":      string,   // any special preferences e.g. "vegetarian food, beach"
  "needs_clarification": boolean, // true if critical info is missing
  "clarification_question": string // question to ask user if needs_clarification is true
}

Critical fields that MUST be present to proceed (if missing, set needs_clarification=true):
- origin or origin_iata
- destination or destination_iata
- depart_date

Common IATA codes to use:
Mumbai=BOM, Delhi=DEL, Bangalore=BLR, Chennai=MAA, Kolkata=CCU, Hyderabad=HYD,
Tokyo=NRT, London=LHR, Paris=CDG, Dubai=DXB, Singapore=SIN, Bangkok=BKK,
New York=JFK, Sydney=SYD, Kuala Lumpur=KUL, Seoul=ICN, Hong Kong=HKG

Return ONLY the JSON object, no explanation."""


def input_parser_agent(state: dict) -> dict:
    """
    Parses user message and extracts structured travel intent.
    Sets needs_clarification=True if origin, destination or date is missing.
    """
    user_input = state.get("user_input", "")
    messages   = state.get("messages", [])

    # build context from conversation history for follow-up messages
    conversation = []
    for msg in messages[-6:]:  # last 6 messages for context
        if hasattr(msg, "type"):
            conversation.append(f"{msg.type}: {msg.content}")

    context = "\n".join(conversation) if conversation else ""
    full_input = f"{context}\nUser: {user_input}" if context else user_input

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=full_input),
    ])

    try:
        raw = response.content.strip()
        # strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except Exception:
        return {
            "needs_clarification":    True,
            "clarification_question": "I couldn't understand your request. Could you please tell me: where are you flying from, where to, and on what dates?",
        }

    # carry forward any previously parsed fields the LLM missed
    for field in ["origin", "origin_iata", "destination", "destination_iata",
                  "depart_date", "return_date", "adults", "travel_class"]:
        if not parsed.get(field) and state.get(field):
            parsed[field] = state[field]

    return {
        "origin":                   parsed.get("origin", ""),
        "origin_iata":              parsed.get("origin_iata", ""),
        "destination":              parsed.get("destination", ""),
        "destination_iata":         parsed.get("destination_iata", ""),
        "dest_country":             parsed.get("dest_country", ""),
        "dest_currency":            parsed.get("dest_currency", "USD"),
        "depart_date":              parsed.get("depart_date", ""),
        "return_date":              parsed.get("return_date", ""),
        "adults":                   parsed.get("adults", 1),
        "travel_class":             parsed.get("travel_class", 1),
        "budget_inr":               parsed.get("budget_inr", 0),
        "trip_type":                parsed.get("trip_type", "round_trip"),
        "preferences":              parsed.get("preferences", ""),
        "needs_clarification":      parsed.get("needs_clarification", False),
        "clarification_question":   parsed.get("clarification_question", ""),
    }
