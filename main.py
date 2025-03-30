#!/usr/bin/env python3
import logging
import os
import sys
from datetime import datetime

import pandas as pd
import requests
from tqdm import tqdm

# TODO: add a lot of logging for easier debuggin in the future

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API-Basis-URLs
LEXOFFICE_BASE_URL = "https://api.lexoffice.io/v1"

def ask_or_get_api_key():
    """Fragt den Benutzer nach dem API-Key oder verwendet den in der Umgebungsvariable."""
    api_key = os.getenv("LEXOFFICE_API_KEY")
    if not api_key:
        api_key = input("Bitte geben Sie Ihren Lexoffice API-Key ein: ").strip()
        os.environ["LEXOFFICE_API_KEY"] = api_key
    else:
        print(f"Der aktuell verwendete API-Key ist: {api_key}")
        new_api_key = input("Drücken Sie Enter, um den aktuellen API-Key zu verwenden, oder geben Sie einen neuen ein: ").strip()
        if new_api_key:
            api_key = new_api_key
            os.environ["LEXOFFICE_API_KEY"] = api_key

    return api_key

def take_cardmarket_orders_via_cmd_input():
    """Nimmt Bestellungen von CardMarket über eine CMD-Eingabe entgegen."""
    
    # TODO: uncomment for production
    # order_exel_path = input("Bitte den Pfad zur Excel-Datei mit den Bestellungen angeben: ").strip("\"'")
    
    # TODO: remove for production
    order_exel_path = '/Users/fabi/Downloads/Fabi.csv'

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

    if not joined_orders:
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
    in der jede Liste von Dictionaries die entsprechenden Werte aus 'description',
    'product id' und 'localized product name' enthält, und entfernt anschließend die
    ursprünglichen Spalten.
    """
    if 'orderid' not in orders.columns:
        logging.error("Spalte 'orderid' wurde in den Daten nicht gefunden.")
        return {}
    
    # Erstelle einen Gruppen-Key: Jede Zeile mit einer nicht-leeren orderid startet eine neue Gruppe.
    orders['group'] = orders['orderid'].notna().cumsum()
    
    # Spalten, die in Listen aggregiert werden sollen
    list_cols = ['description', 'product id', 'localized product name']
    
    # Aggregations-Dictionary erstellen:
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
    
    # Erstelle die neue Spalte "items" mit einer Liste von Dictionaries für jede Gruppe.
    shipments['items'] = shipments.apply(
        lambda row: [
            {"description": d, "product id": p, "localized product name": n} 
            for d, p, n in zip(row["description"], row["product id"], row["localized product name"])
        ], 
        axis=1
    )
    
    # Entferne die originalen Spalten
    shipments.drop(columns=list_cols, inplace=True)
    
    return shipments

def create_invoice_payload(order):
    """Übersetzt eine CardMarket-Bestellung in ein lexoffice-Rechnungs-Payload-Format."""
    # TODO: uncomment for production
    # buyer_info = order.get('buyer')
    # if not buyer_info:
    #     logging.error("Keine Käuferinformationen gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
    #     return None # No success
    
    # TODO: add actual data for production
    customer = {
        "name": "Some Name",
        "address": {
            "street": "Some Street",
            "zip": "Some Zip",
            "city": "Some City",
            "countryCode": "DE"
        }
    }
    voucher_date = order.get('dateOfPurchase')
    
    if not voucher_date:
        logging.error("Kein Datum gefunden. Kann keine Rechnung für Bestellung mit Liefernummer (Shipment Nr.) {} erstellen.".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    
    line_items = []
    articles = order.get('articles', [])
    for article in articles:
        price = article.get("price")
        name = article.get("name")
        quantity = article.get("quantity")
        
        if not name:
            logging.error(f"Artikel {article['product_id']} für Kunden '{customer['name']}' hat keinen Namen. Überspringe die Komplette Bestellung. Bitte füge den Artikel manuell zu Lexoffice hinzu.")
            return None
        
        if not price:
            logging.error(f"Artikel {name} für Kunden '{customer['name']}' hat keinen Preis. Überspringe die Komplette Bestellung. Bitte füge den Artikel manuell zu Lexoffice hinzu.")
            return None
        
        if not quantity:
            logging.error(f"Artikel {name} für Kunden '{customer['name']}' hat keine Menge. Überspringe die Komplette Bestellung. Bitte füge den Artikel manuell zu Lexoffice hinzu.")
            return None
        
        item = {
            "type": "custom",
            "name": name,
            "quantity": quantity,
            "unitName": "Stück",
            "unitPrice": {
                "currency": order.get("currency", "EUR"),
                "netAmount": price,
                "taxRatePercentage": 19
            },
            "discountPercentage": 0,
            "lineItemAmount": price
        }
        line_items.append(item)
    shipping_cost = order.get("shippingCost")
    
    if not shipping_cost:
        logging.warn(f"Bestellung {order.get('shipment_nr', 'Unbekannt')} für Kunden '{customer['name']}' hat keine Versandkosten. Sollte das nicht richtig sein, bitte manuell in Lexoffice hinzufügen.")
        shipping_cost = 0
        
    if shipping_cost:
        shipping_item = {
            "type": "custom",
            "name": "Versandkosten",
            "quantity": 1,
            "unitName": "Pauschale",
            "unitPrice": {
                "currency": order.get("currency", "EUR"),
                "netAmount": shipping_cost,
                "taxRatePercentage": 19
            },
            "discountPercentage": 0,
            "lineItemAmount": shipping_cost
        }
        line_items.append(shipping_item)
    
    payload = {
        "customer": customer,
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
    # TODO: ask for api key if not set in env variables and then put into env variables
    api_key = ask_or_get_api_key()
    orders = take_cardmarket_orders_via_cmd_input()

    success_count = 0
    for order in tqdm(orders, "Rechnungen werden übertragen..."):
        invoice_payload = create_invoice_payload(order)
        # TODO: remove for production
        exit()
        if not invoice_payload:
            logging.error(f"Fehler beim Erstellen der Rechnung für Bestellung {order.get('shipment_nr', 'Unbekannt')}.")
            continue
        
        # TODO: uncomment for production
        # if send_invoice_to_lexoffice(invoice_payload, api_key):
        #     success_count += 1
        # else:
        #     logging.error(f"Rechnung für Bestellung {order.get('id', 'Unbekannt')} konnte nicht übertragen werden.")
    logging.info(f"Übertragung abgeschlossen: {success_count} von {len(orders)} Rechnungen erfolgreich übertragen.")
    input("Drücken Sie Enter, um das Programm zu beenden.")

if __name__ == '__main__':
    main()