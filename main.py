#!/usr/bin/env python3
import datetime
import logging
import os
import sys

import pandas as pd
import requests
from tqdm import tqdm

# TODO: add a lot of logging for easier debuggin in the future

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Konfiguration über Environment-Variablen
LEXOFFICE_API_KEY = os.getenv("LEXOFFICE_API_KEY")

if not all([LEXOFFICE_API_KEY]):
    logging.error("Fehlende Konfigurationsvariablen. Bitte alle erforderlichen Environment Variables setzen.")
    sys.exit(1)

# API-Basis-URLs
LEXOFFICE_BASE_URL = "https://api.lexoffice.io/v1"

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
    """Liest eine CSV- oder Excel-Datei und gibt die Daten als pandas DataFrame zurück."""
    import pandas as pd
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except pd.errors.ParserError:
            df = pd.read_csv(file_path, encoding='utf-8', sep=';')
    elif ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path)
    else:
        logging.error("Unsupported file type: " + ext)
        sys.exit(1)
    # Standardize column names: trim and lower case
    df.columns = df.columns.str.strip().str.lower()
    return df

def join_shipment_data(file_path_or_orders):
    """
    Gruppiert Daten (als DataFrame oder Liste von Dictionaries) nach Shipment Number.
    Die Spalte wird standardisiert (lower case) und es wird pandas.groupby() verwendet.
    """
    if isinstance(file_path_or_orders, pd.DataFrame):
        df = file_path_or_orders
    elif isinstance(file_path_or_orders, list):
        df = pd.DataFrame(file_path_or_orders)
    else:
        df = extract_csv_data(file_path_or_orders)
    if 'shipment nr.' not in df.columns:
        logging.error("Spalte 'shipment nr.' wurde in den Daten nicht gefunden.")
        return {}
    shipments = {}
    for shipment_nr, group in df.groupby('shipment nr.'):
        articles = []
        for _, row in group.iterrows():
            article_info = {
                "product_id": row.get("product id"),
                "article": row.get("article"),
                "product_name": row.get("localized product name"),
                "expansion": row.get("expansion"),
                "category": row.get("category"),
                "amount": row.get("amount"),
                "article_price": row.get("article value"),
                "total_price": row.get("total"),
                "currency": row.get("currency"),
                "comments": row.get("comments"),
            }
            articles.append(article_info)
        shipments[shipment_nr] = {
            "shipment_nr": shipment_nr,
            "articles": articles
        }
    return shipments

def create_invoice_payload(order):
    """Übersetzt eine CardMarket-Bestellung in ein lexoffice-Rechnungs-Payload-Format."""
    buyer_info = order.get('buyer', {})
    customer = {
        "name": buyer_info.get("username", "Unbekannt"),
        "address": {
            "street": buyer_info.get("street", ""),
            "zip": buyer_info.get("zip", ""),
            "city": buyer_info.get("city", ""),
            "countryCode": buyer_info.get("countryCode", "DE")
        }
    }
    voucher_date = order.get('dateReceived', datetime.date.today().isoformat())
    line_items = []
    articles = order.get('articles', [])
    for article in articles:
        item = {
            "type": "custom",
            "name": article.get("name", "Artikel"),
            "quantity": article.get("quantity", 1),
            "unitName": "Stück",
            "unitPrice": {
                "currency": order.get("currency", "EUR"),
                "netAmount": article.get("price", 0.0),
                "taxRatePercentage": 19
            }
        }
        line_items.append(item)
    shipping_cost = order.get("shippingCost")
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
            }
        }
        line_items.append(shipping_item)
    
    payload = {
        "customer": customer,
        "voucherDate": voucher_date,
        "lineItems": line_items,
        "taxConditions": {
            "taxType": "net"
        }
    }
    return payload

def send_invoice_to_lexoffice(invoice_payload):
    """Sendet eine Rechnung an die lexoffice API."""
    endpoint = f"{LEXOFFICE_BASE_URL}/invoices"
    headers = {
        "Authorization": f"Bearer {LEXOFFICE_API_KEY}",
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
    orders = take_cardmarket_orders_via_cmd_input()
    print(next(iter(orders.values())))
    exit(0)

    success_count = 0
    for order in tqdm(joined_orders, "Rechnungen werden übertragen..."):
        invoice_payload = create_invoice_payload(order)
        if send_invoice_to_lexoffice(invoice_payload):
            success_count += 1
        else:
            logging.error(f"Rechnung für Bestellung {order.get('id', 'Unbekannt')} konnte nicht übertragen werden.")
    logging.info(f"Übertragung abgeschlossen: {success_count} von {len(orders)} Rechnungen erfolgreich übertragen.")

if __name__ == '__main__':
    main()