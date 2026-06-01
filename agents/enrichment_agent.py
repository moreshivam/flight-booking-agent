from concurrent.futures import ThreadPoolExecutor, as_completed

from tools.weather_tool  import get_weather,        format_weather_for_llm
from tools.country_tool  import get_country_info,   format_country_for_llm
from tools.currency_tool import get_exchange_rate,  format_currency_for_llm


def enrichment_agent(state: dict) -> dict:
    """
    Fetches weather, country info, and currency rate IN PARALLEL.
    All 3 API calls run simultaneously — no waiting for one to finish before starting the next.
    """
    destination  = state.get("destination", "")
    dest_country = state.get("dest_country", "") or destination
    dest_currency = state.get("dest_currency", "USD")
    depart_date  = state.get("depart_date", "")
    return_date  = state.get("return_date", "") or depart_date

    if not destination or not depart_date:
        return {
            "weather_data":    {},
            "country_info":    {},
            "currency_info":   {},
            "weather_summary":  "No destination or date provided.",
            "country_summary":  "No destination provided.",
            "currency_summary": "No destination provided.",
        }

    # define each task as (name, fn, args)
    tasks = {
        "weather":  (get_weather,        (destination, depart_date, return_date)),
        "country":  (get_country_info,   (dest_country,)),
        "currency": (get_exchange_rate,  ("INR", dest_currency, 1.0)),
    }

    results = {}

    # run all 3 in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fn, *args): name
            for name, (fn, args) in tasks.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e)}

    weather_data  = results.get("weather",  {})
    country_info  = results.get("country",  {})
    currency_info = results.get("currency", {})

    return {
        "weather_data":    weather_data,
        "country_info":    country_info,
        "currency_info":   currency_info,
        "weather_summary":  format_weather_for_llm(weather_data),
        "country_summary":  format_country_for_llm(country_info),
        "currency_summary": format_currency_for_llm(currency_info),
    }
