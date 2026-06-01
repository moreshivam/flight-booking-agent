# AI Travel Booking Agent

An end-to-end AI-powered travel planning system built with **LangGraph**. Takes a natural language request like *"Mumbai to Tokyo, August 15–22, 2 adults, economy"* and returns real flights, hotels, weather forecast, country info, currency rates, an interactive map, and a full day-by-day itinerary — all automated.

---

## Architecture

```
User Input (natural language)
        ↓
┌─────────────────────────────────────────────────────┐
│                  LANGGRAPH WORKFLOW                  │
│                                                     │
│  input_parser ──► [needs info?] ──YES──► ask_user  │
│       ↓ NO                                          │
│  flight_search   (SerpAPI Google Flights)           │
│       ↓                                             │
│  enrichment      (Weather + Country + Currency)     │
│       ↓          (3 APIs run in PARALLEL)           │
│  hotel_search    (SerpAPI Google Hotels)            │
│       ↓                                             │
│  itinerary       (Groq LLM + Folium map)            │
│       ↓                                             │
│  final           (Summary card + full plan)         │
└─────────────────────────────────────────────────────┘
        ↓
Streamlit UI  →  Flights | Hotels | Itinerary | Map
               →  Download PDF | Add to Calendar
```

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| LLM | Groq (Llama 3.3 70B) | Free |
| Agent Orchestration | LangGraph | Free (open source) |
| Memory | SQLite (`langgraph-checkpoint-sqlite`) | Free (no server) |
| Flights | SerpAPI Google Flights | Free (100/month) |
| Hotels | SerpAPI Google Hotels | Free (same key) |
| Weather | Open-Meteo | Free (no API key) |
| Country Info | REST Countries API | Free (no API key) |
| Currency | ExchangeRate-API | Free (1500/month) |
| Maps | Folium + streamlit-folium | Free (open source) |
| Charts | Plotly | Free (open source) |
| PDF Export | FPDF2 | Free (open source) |
| Calendar Export | icalendar | Free (open source) |
| Frontend | Streamlit | Free (open source) |

**Total cost to run: $0** (within free tier limits)

---

## Project Structure

```
flight-agent/
│
├── .env                        # API keys (never commit this)
├── .gitignore
├── requirements.txt
├── main.py                     # LangGraph StateGraph + CLI runner
├── frontend.py                 # Streamlit web UI
├── test_agent.py               # Tool + agent tests
│
├── agents/
│   ├── input_parser.py         # LLM extracts: origin, dest, dates, pax, budget
│   ├── flight_agent.py         # Calls SerpAPI Google Flights
│   ├── enrichment_agent.py     # Weather + Country + Currency (parallel)
│   ├── hotel_agent.py          # Calls SerpAPI Google Hotels (budget-aware)
│   ├── itinerary_agent.py      # LLM builds day-by-day plan + Folium map
│   └── final_agent.py          # Formats summary card + packages output
│
├── tools/
│   ├── flight_tool.py          # SerpAPI Google Flights wrapper
│   ├── hotel_tool.py           # SerpAPI Google Hotels wrapper
│   ├── weather_tool.py         # Open-Meteo forecast (no key needed)
│   ├── country_tool.py         # REST Countries API (no key needed)
│   ├── currency_tool.py        # ExchangeRate-API live rates
│   └── map_tool.py             # Folium interactive map generator
│
├── memory/
│   └── checkpointer.py         # SQLite checkpointer setup
│
├── utils/
│   ├── ssl_patch.py            # SSL fix for Windows Python environments
│   ├── pdf_export.py           # FPDF2 itinerary PDF generator
│   └── calendar_export.py      # icalendar .ics export
│
└── data/
    └── travel_memory.db        # SQLite DB (auto-created on first run)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/moreshivam/flight-booking-agent.git
cd flight-booking-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get your API keys

| Key | Where to get it | Free tier |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) | Unlimited (rate limited) |
| `SERPAPI_KEY` | [serpapi.com/dashboard](https://serpapi.com/dashboard) | 100 searches/month |
| `EXCHANGERATE_API_KEY` | [app.exchangerate-api.com](https://app.exchangerate-api.com/dashboard) | 1500 requests/month |

> **Open-Meteo** and **REST Countries** require no API key.

### 4. Configure `.env`

```env
GROQ_API_KEY=your_groq_key_here
SERPAPI_KEY=your_serpapi_key_here
EXCHANGERATE_API_KEY=your_exchangerate_key_here
```

---

## Running

### CLI (test locally)

```bash
python main.py
```

```
You: I want to fly from Mumbai to Tokyo, August 15 to 22 2026, 2 adults economy
Agent is thinking...

FLIGHTS
  1. Cathay Pacific | 1 stop | 11h 45m | INR 1,32,198
  ...

HOTELS
  1. Shinjuku Granbell Hotel | 4-star | Rating 4.3/5 | ¥12,500/night
  ...

ITINERARY
  Day 1 - Aug 15 ⛅ Partly cloudy | 24°C - 31°C
  - Morning: Arrive at Narita, check in...
  ...
```

### Web UI

```bash
streamlit run frontend.py
```

### Run tests

```bash
python test_agent.py
```

---

## How It Works

### LangGraph State

All agents communicate through a shared `TravelState` TypedDict — no agent calls another agent directly. Think of it as a whiteboard: each agent reads what's there, adds their result, and passes it on.

```python
class TravelState(TypedDict):
    user_input:        str
    origin_iata:       str       # "BOM"
    destination_iata:  str       # "NRT"
    depart_date:       str       # "2026-08-15"
    adults:            int       # 2
    flight_results:    dict      # ← flight_agent writes here
    weather_data:      dict      # ← enrichment_agent writes here
    hotel_results:     dict      # ← hotel_agent writes here
    itinerary:         str       # ← itinerary_agent writes here
    final_plan:        str       # ← final_agent writes here
    ...
```

### Conditional Routing

After `input_parser`, the graph checks if all critical fields (origin, destination, date) are present. If not, it routes to `ask_user` which returns a clarification question and ends the graph. The user's reply re-invokes the parser with conversation history, so they never need to repeat themselves.

### Parallel Enrichment

The `enrichment_agent` uses Python's `ThreadPoolExecutor` to run Weather, Country, and Currency API calls simultaneously:

```
Sequential:  weather(2s) + country(1s) + currency(1s) = 4s
Parallel:    all 3 at once                             = ~2s
```

### Budget-Aware Hotel Search

If the user provides a budget, the hotel agent:
1. Reads the live exchange rate from state (already fetched by enrichment agent)
2. Calculates max price per night = `(budget_inr × rate / nights) × 40%`
3. Passes `max_price` to SerpAPI to filter results automatically

### Memory

Every conversation is saved to SQLite by `thread_id`. Users can continue planning across sessions — the agent remembers their previous destination, dates, and preferences.

---

## Key Design Decisions

**Why SerpAPI over AviationStack?**
The reference project's flight tool ignored the search query entirely — it fetched 5 random live flights with no origin, destination, or date filtering. SerpAPI Google Flights takes real parameters and returns actual bookable options with prices.

**Why SerpAPI for hotels over Tavily?**
Tavily is a web search engine — it returns blog snippets and travel articles, not real hotel availability or pricing. SerpAPI Google Hotels returns structured data: hotel name, star rating, guest rating, price per night, total price, amenities, and GPS coordinates.

**Why SQLite over PostgreSQL?**
SQLite is file-based and requires zero server setup. For a single-user or small-scale deployment, it is equally capable and dramatically simpler to run.

**Why Groq over OpenAI?**
Groq runs Llama 3.3 70B with extremely fast inference (tokens/sec) at zero cost on the free tier. No credit card required.

---

## What Each Agent Does

| Agent | Input from State | Tool Called | Output to State |
|---|---|---|---|
| `input_parser` | `user_input` | Groq LLM | origin, dest, dates, pax, budget |
| `flight_agent` | origin, dest, dates, pax | `flight_tool` | `flight_results`, `flight_summary` |
| `enrichment_agent` | destination, dates | weather + country + currency tools | `weather_data`, `country_info`, `currency_info` |
| `hotel_agent` | dest, dates, pax, budget | `hotel_tool` | `hotel_results`, `hotel_summary` |
| `itinerary_agent` | all summaries | Groq LLM + `map_tool` | `itinerary`, `map_html` |
| `final_agent` | itinerary + top picks | Groq LLM | `final_plan`, `final_summary` |

---

## Example Output

**Input:**
```
Mumbai to Tokyo, August 15–22 2026, 2 adults, economy, budget ₹3,00,000
```

**Output:**
- 3 best flights (Cathay Pacific, Malaysia Airlines, etc.) with prices in INR
- 5 hotels sorted by price with ratings and amenities
- 7-day weather forecast for Tokyo
- Japan country info: visa required, JPY currency, Japanese language, left-hand drive
- Live rate: 1 INR = 1.67 JPY with quick reference table
- Full day-by-day itinerary with weather overlay and local tips
- Interactive Folium map: BOM → NRT flight route + hotel pins
- Downloadable PDF itinerary
- `.ics` calendar file for Google/Apple Calendar

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Built by [Shivam More](https://github.com/moreshivam)
