#!/usr/bin/env python3
import logging
import os
import re
import sys
import time
from datetime import datetime
from decimal import Decimal

import pycountry
import pytz
import requests
from dotenv import load_dotenv, set_key
from tqdm import tqdm

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API-Basis-URLs
LEXOFFICE_BASE_URL = "https://api.lexoffice.io/v1"

env_file = ".env"
load_dotenv(dotenv_path=env_file)

def ask_or_get_api_key():
    """Fragt den Benutzer nach dem API-Key oder verwendet den in der .env-Datei."""
    api_key = os.getenv("LEXOFFICE_API_KEY")
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
        exit()
        
    return api_key

def take_cardmarket_orders_via_cmd_input():
    """Nimmt Bestellungen von CardMarket über eine CMD-Eingabe entgegen."""
    
    order_exel_path = input("Bitte den Pfad zur Excel-Datei mit den Bestellungen angeben: ").strip("\"'")

    if not order_exel_path.endswith(".csv"):
        logging.error("Bitte eine CSV-Datei angeben.")
        sys.exit(1)
    if not os.path.isfile(order_exel_path):
        logging.error(f"Die Datei {order_exel_path} existiert nicht.")
        sys.exit(1)

    orders = extract_csv_data(order_exel_path)

    if orders.empty:
        logging.error("Keine Bestellungen gefunden.")
        sys.exit(1)

    joined_orders = join_shipment_data(orders)

    if joined_orders.empty:
        logging.error("Keine Bestellungen nach dem Zusammenfügen von Bestellungen gefunden.")
        sys.exit(1)

    return joined_orders

def extract_csv_data(file_path):
    """Liest eine CSV-Datei und gibt die Daten als pandas DataFrame zurück."""
    import pandas as pd
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except pd.errors.ParserError:
            df = pd.read_csv(file_path, encoding='utf-8', sep=';')
    else:
        logging.error("Unsupported file type: " + ext)
        sys.exit(1)
    # Standardize column names: trim and lower case
    df.columns = df.columns.str.strip().str.lower()
    return df

def join_shipment_data(orders):
    """
    Fügt Zeilen zusammen, die zur selben Bestellung gehören, erstellt eine neue Spalte 'items',
    in der jede Liste von Dictionaries die entsprechenden Werte enthält.
    """
    import logging  # sicherstellen, dass logging importiert ist
    
    if 'orderid' not in orders.columns:
        logging.error("Spalte 'orderid' wurde in den Daten nicht gefunden.")
        return {}
    
    # Erstelle einen Gruppen-Key: Jede Zeile mit einer nicht-leeren orderid startet eine neue Gruppe.
    orders['group'] = orders['orderid'].notna().cumsum()
    
    # Spalten, die aggregiert werden sollen
    list_cols = ['description', 'product id', 'localized product name']
    
    # Aggregations-Dictionary:
    # - Für list_cols: kombiniere die Werte in einer Liste.
    # - Für alle anderen Spalten (außer 'group'): nimm den ersten Wert.
    agg_dict = {col: (lambda x: list(x)) for col in list_cols}
    for col in orders.columns:
        if col not in list_cols + ['group']:
            agg_dict[col] = 'first'
    
    # Gruppieren und aggregieren
    shipments = orders.groupby('group', sort=False).agg(agg_dict).reset_index(drop=True)
    
    # Konvertiere orderid zu Integer, um das Anhängen von .0 zu vermeiden
    shipments['orderid'] = shipments['orderid'].astype(int)
    
    # Erstelle die neue Spalte "items". Für jede Zeile:
    #  - splitte jeden Eintrag in "description" nach " - "
    #  - verwende die einzelnen Teile zur Befüllung der neuen Dictionary-Keys
    shipments['articles'] = shipments.apply(
        lambda row: [
            {
                "description": extract_quantity_and_name(parts[0].strip())[1] if len(parts) > 0 else None,
                "quantity": extract_quantity_and_name(parts[0].strip())[0] if len(parts) > 0 else None,
                "number": parts[1].strip() if len(parts) > 1 else None,
                "rarity": parts[2].strip() if len(parts) > 2 else None,
                "card condition": parts[3].strip() if len(parts) > 3 else None,
                "language": parts[4].strip() if len(parts) > 4 else None,
                "price per card": parts[-1].strip() if len(parts) > 5 else None,
                "product id": p,
                "name": n
            }
            for d, p, n in zip(row["description"], row["product id"], row["localized product name"])
            for parts in [d.split(" - ")]
        ],
        axis=1
    )
    
    # Entferne die originalen Spalten
    shipments.drop(columns=list_cols, inplace=True)
    
    return shipments

def extract_quantity_and_name(s):
    match = re.search(r"(\d{1,2})x\s+([^(]+)", s)
    if match:
        factor = int(match.group(1))
        name = match.group(2).strip()
        return factor, name
    return None

def get_country_code(country_name: str) -> str:
    # Try to fetch by the exact name
    country = pycountry.countries.get(name=country_name)
    if country:
        return country.alpha_2  # For ISO alpha-2 code
    # Fallback: check if the provided name is a substring (case-insensitive)
    for c in pycountry.countries:
        if country_name.lower() in c.name.lower():
            return c.alpha_2
    raise ValueError(f"Country code for '{country_name}' not found.")

def parse_date(date_str: str) -> datetime:
    for fmt in ("%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"No valid date format found for {date_str}")

def create_invoice_payload(order):
    """Übersetzt eine CardMarket-Bestellung in ein lexoffice-Rechnungs-Payload-Format."""
    name = order.get('name')
    street = order.get('street')
    city_and_postal_code = order.get('city')
    country = order.get('country')
    
    if not name:
        logging.error("Kein Name gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    if not street:
        logging.error("Keine Straße gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    if not city_and_postal_code:
        logging.error("Kein Stadt- und Postleitzahl gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    if not country:
        logging.error("Kein Land gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    city = city_and_postal_code.split(" ")[1].strip()
    postal_code = city_and_postal_code.split(" ")[0].strip()
    country_code = get_country_code(country)
    
    customer = {
        "name": order.get('name'),
        "address": {
            "street": street,
            "zip": postal_code,
            "city": city,
            "countryCode": country_code
        }
    }
    unformatted_voucher_date = order.get('date of purchase')
    
    if not unformatted_voucher_date:
        logging.error("Kein Datum gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    dt = parse_date(unformatted_voucher_date)
    german_tz = pytz.timezone("Europe/Berlin")
    localized_dt = german_tz.localize(dt)
    voucher_date = localized_dt.isoformat(timespec='milliseconds')    
    
    if not voucher_date:
        logging.error("Kein Datum gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    line_items = []
    articles = order.get('articles')
    
    if not articles:
        logging.error(f"Keine Artikel gefunden für Bestellung mit Liefernummer (Shipment Nr.) {order.get('shipment_nr', 'Unbekannt')}.")
        return None
    
    for article in articles:
        unit_price_with_currency = article.get("price per card")
        name = article.get("name")
        quantity = article.get("quantity")
        if not name:
            logging.error(f"Artikel {article['product id']} für Kunden '{customer['name']}' hat keinen Namen. Überspringe die Komplette Bestellung. Bitte füge den Artikel manuell zu Lexoffice hinzu.")
            return None
        
        if not unit_price_with_currency:
            logging.error(f"Artikel {name} für Kunden '{customer['name']}' hat keinen Preis. Überspringe die Komplette Bestellung. Bitte füge den Artikel manuell zu Lexoffice hinzu.")
            return None
        
        if not quantity:
            logging.error(f"Artikel {name} für Kunden '{customer['name']}' hat keine Menge. Überspringe die Komplette Bestellung. Bitte füge den Artikel manuell zu Lexoffice hinzu.")
            return None
        
        unit_price = unit_price_with_currency.split(" ")[0]
        unit_price_formatted = Decimal(unit_price.replace(",", "."))
        currency = unit_price_with_currency.split(" ")[1]
        
        item = {
            "type": "custom",
            "name": name,
            "quantity": quantity,
            "unitName": "Stück",
            "unitPrice": {
                "currency": currency,
                "netAmount": str(unit_price_formatted),
                "taxRatePercentage": 0 # "Line items in vatfree invoices must not contain taxes."
            },
            "discountPercentage": 0,
            "lineItemAmount": str(unit_price_formatted * quantity)
        }
        line_items.append(item)
        
    shipping_cost = order.get("shipment costs")

    if not shipping_cost:
        logging.warning(f"Bestellung {order.get('shipment_nr', 'Unbekannt')} für Kunden '{customer['name']}' hat keine Versandkosten. Sollte das nicht richtig sein, bitte manuell in Lexoffice hinzufügen.")
        shipping_cost = 0
        
    shipping_cost_formatted = Decimal(shipping_cost.replace(",", "."))
    
    if shipping_cost:
        shipping_item = {
            "type": "custom",
            "name": "Versandkosten",
            "quantity": 1,
            "unitName": "Pauschale",
            "unitPrice": {
                "currency": order.get("currency", "EUR"),
                "netAmount": str(shipping_cost_formatted),
                "taxRatePercentage": 0 # "Line items in vatfree invoices must not contain taxes." 
            },
            "discountPercentage": 0,
            "lineItemAmount": shipping_cost
        }
        line_items.append(shipping_item)
    
    # TODO: add address of own company?
    address = {
    "name": "Bike & Ride GmbH & Co. KG",
        "supplement": "Gebäude 10",
        "street": "Musterstraße 42",
        "city": "Freiburg",
        "zip": "79112",
        "countryCode": "DE"
    }
    
    shipping_conditions = {
        "shippingDate": voucher_date,
        "shippingType": "delivery"
    }
      
    payload = {
        "customer": customer,
        "address": address,
        "totalPrice": {
            "currency": "EUR"
        },
        "shippingConditions": shipping_conditions,
        "archived": False,
        "voucherDate": voucher_date,
        "lineItems": line_items,
        "taxConditions": {
            "taxType": "vatfree"
        }
    }
    return payload

def send_invoice_to_lexoffice(invoice_payload, api_key):
    """Sendet eine Rechnung an die lexoffice API."""
    endpoint = f"{LEXOFFICE_BASE_URL}/invoices"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(endpoint, json=invoice_payload, headers=headers)
        if response.status_code == 201:
            logging.info("Rechnung erfolgreich in Lexoffice angelegt.")
            return True
        else:
            logging.error(f"Fehler beim Anlegen der Rechnung: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Ausnahme beim Senden der Rechnung: {e}")
        return False

def main():
    logging.info("Starte den Abgleich von CardMarket zu Lexoffice.")
    api_key = ask_or_get_api_key()
    orders = take_cardmarket_orders_via_cmd_input()

    success_count = 0
    for _, order in tqdm(orders.iterrows(), total=orders.shape[0], desc="Processing rows"):
        invoice_payload = create_invoice_payload(order)
        if not invoice_payload:
            logging.error(f"Fehler beim Erstellen der Rechnung für Bestellung {order.get('shipment_nr', 'Unbekannt')}.")
            continue
        
        if send_invoice_to_lexoffice(invoice_payload, api_key):
            success_count += 1
        else:
            logging.error(f"Rechnung für Bestellung {order.get('id', 'Unbekannt')} konnte nicht übertragen werden.")
        
        # Required to avoid hitting the API rate limit
        time.sleep(0.5)
        
    logging.info(f"Übertragung abgeschlossen: {success_count} von {len(orders)} Rechnungen erfolgreich übertragen.")
    input("Drücken Sie Enter, um das Programm zu beenden.")

if __name__ == '__main__':
    main()