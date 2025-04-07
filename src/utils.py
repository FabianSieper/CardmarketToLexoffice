import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional, Tuple

import pycountry
from dotenv import set_key


def ask_or_get_api_key() -> str:
    env_file: str = ".env"
    api_key: Optional[str] = os.getenv("LEXOFFICE_API_KEY")
    if not api_key:
        api_key = input("Bitte geben Sie Ihren Lexoffice API-Key ein: ").strip()
        set_key(env_file, "LEXOFFICE_API_KEY", api_key)
    else:
        print(f"Der aktuell verwendete API-Key ist: {api_key}")
        new_api_key = input("Drücken Sie Enter, um den aktuellen API-Key zu verwenden, oder geben Sie einen neuen ein: ").strip()
        if new_api_key:
            api_key = new_api_key
            set_key(env_file, "LEXOFFICE_API_KEY", api_key)
    if not api_key:
        logging.error("Es wurde kein API Key zur Verfügung gestellt.")
        input("Drücke Enter um fortzufahren")
        sys.exit(1)
    return api_key

def parse_date(date_str: str) -> datetime:
    for fmt in ("%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"No valid date format found for {date_str}")

def get_country_code(country_name: str) -> str:
    country = pycountry.countries.get(name=country_name)
    if country:
        return country.alpha_2
    for c in pycountry.countries:
        if country_name.lower() in c.name.lower():
            return c.alpha_2
    raise ValueError(f"Country code for '{country_name}' not found.")

def extract_quantity_and_name(s: str) -> Optional[Tuple[int, str]]:
    match = re.search(r"(\d{1,2})x\s+([^(]+)", s)
    if match:
        factor: int = int(match.group(1))
        name: str = match.group(2).strip()
        return factor, name
    return None