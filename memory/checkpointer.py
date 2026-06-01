import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "travel_memory.db")


def get_checkpointer() -> SqliteSaver:
    """
    Returns a SQLite checkpointer for LangGraph.
    Automatically creates the data/ folder and DB file if they don't exist.
    """
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return SqliteSaver(conn)
