import json
import os

# Path to the JSON file
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_LIST_FILE = os.path.join(DATA_DIR, "data", "stock_list.json")

def load_stock_list():
    """
    Load stock list from JSON file.
    In a real scenario, this could also fetch from an API or DB.
    """
    if os.path.exists(STOCK_LIST_FILE):
        try:
            with open(STOCK_LIST_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading stock list: {e}")
            return []
    return []

# Placeholder for dynamic updater
def update_stock_list_from_external():
    """
    Could be used to fetch trending stocks from an external API
    and update stock_list.json
    """
    pass

# Load on module import or explicit call
STOCKS_DB = load_stock_list()
