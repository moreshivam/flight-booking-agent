"""
Quick test script — run each layer independently to verify everything works.
Usage: python test_agent.py
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from utils.ssl_patch import apply as _apply_ssl_patch
_apply_ssl_patch()


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── Test 1: Weather Tool ───────────────────────────────────────
separator("TEST 1: Weather Tool (Open-Meteo — no API key)")
try:
    from tools.weather_tool import get_weather, format_weather_for_llm
    result = get_weather("Tokyo", "2026-08-15", "2026-08-22")
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    else:
        print(format_weather_for_llm(result))
        print("  ✓ Weather tool works")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 2: Country Tool ───────────────────────────────────────
separator("TEST 2: Country Tool (REST Countries — no API key)")
try:
    from tools.country_tool import get_country_info, format_country_for_llm
    result = get_country_info("Japan")
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    else:
        print(format_country_for_llm(result))
        print("  ✓ Country tool works")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 3: Currency Tool ──────────────────────────────────────
separator("TEST 3: Currency Tool (ExchangeRate-API)")
try:
    from tools.currency_tool import get_exchange_rate, format_currency_for_llm
    result = get_exchange_rate("INR", "JPY", 1.0)
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    else:
        print(format_currency_for_llm(result))
        print("  ✓ Currency tool works")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 4: Flight Tool ────────────────────────────────────────
separator("TEST 4: Flight Tool (SerpAPI Google Flights)")
try:
    from tools.flight_tool import search_flights, format_flights_for_llm
    result = search_flights(
        origin="BOM", destination="NRT",
        depart_date="2026-08-15", return_date="2026-08-22",
        adults=2, travel_class=1, currency="INR"
    )
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    else:
        print(format_flights_for_llm(result))
        print("  ✓ Flight tool works")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 5: Hotel Tool ─────────────────────────────────────────
separator("TEST 5: Hotel Tool (SerpAPI Google Hotels)")
try:
    from tools.hotel_tool import search_hotels, format_hotels_for_llm
    result = search_hotels(
        destination="Tokyo",
        check_in="2026-08-15", check_out="2026-08-22",
        adults=2, currency="JPY"
    )
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    else:
        print(format_hotels_for_llm(result))
        print("  ✓ Hotel tool works")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 6: Map Tool ───────────────────────────────────────────
separator("TEST 6: Map Tool (Folium)")
try:
    from tools.map_tool import build_travel_map
    html = build_travel_map("BOM", "NRT", destination_city="Tokyo")
    if html:
        print(f"  ✓ Map generated ({len(html):,} chars of HTML)")
    else:
        print("  ERROR: Map returned None")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 7: Input Parser Agent ────────────────────────────────
separator("TEST 7: Input Parser Agent (Groq LLM)")
try:
    from agents.input_parser import input_parser_agent
    result = input_parser_agent({
        "user_input": "I want to fly from Mumbai to Tokyo, August 15 to 22, 2 adults, economy",
        "messages": []
    })
    print(f"  Origin:      {result.get('origin')} ({result.get('origin_iata')})")
    print(f"  Destination: {result.get('destination')} ({result.get('destination_iata')})")
    print(f"  Dates:       {result.get('depart_date')} → {result.get('return_date')}")
    print(f"  Adults:      {result.get('adults')}")
    print(f"  Needs clarification: {result.get('needs_clarification')}")
    print("  ✓ Input parser works")
except Exception as e:
    print(f"  FAILED: {e}")


# ── Test 8: Full Agent Run ─────────────────────────────────────
separator("TEST 8: Full Agent Pipeline")
try:
    from main import run_travel_agent
    print("  Running full pipeline: Mumbai → Tokyo, Aug 15-22, 2 adults...")
    print("  (This may take 15-30 seconds)")
    result = run_travel_agent(
        "I want to fly from Mumbai to Tokyo from August 15 to August 22 2026, 2 adults, economy class",
        thread_id="test_session_001"
    )
    if result.get("needs_clarification"):
        print(f"  Clarification needed: {result['clarification_question']}")
    elif result.get("final_summary"):
        print("\n--- FINAL SUMMARY ---")
        print(result["final_summary"])
        print("  ✓ Full pipeline works")
    else:
        print(f"  ERROR: {result.get('error', 'Unknown error')}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n" + "="*60)
print("  Testing complete.")
print("="*60 + "\n")
