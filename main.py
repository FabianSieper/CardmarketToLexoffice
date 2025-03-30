#!/usr/bin/env python3
import datetime
import logging
import os
import sys

import requests

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Konfiguration über Environment-Variablen
LEXOFFICE_API_KEY = os.getenv("LEXOFFICE_API_KEY")

if not all([LEXOFFICE_API_KEY]):
    logging.error("Fehlende Konfigurationsvariablen. Bitte alle erforderlichen Environment Variables setzen.")
    sys.exit(1)

# API-Basis-URLs
LEXOFFICE_BASE_URL = "https://api.lexoffice.io/v1"

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
    orders = # TODO: take orders from cmd input via xlsx file
    if not orders:
        logging.info("Keine Bestellungen für den letzten Monat gefunden. Beende das Skript.")
        sys.exit(0)
    
    success_count = 0
    for order in orders:
        invoice_payload = create_invoice_payload(order)
        if send_invoice_to_lexoffice(invoice_payload):
            success_count += 1
        else:
            logging.error(f"Rechnung für Bestellung {order.get('id', 'Unbekannt')} konnte nicht übertragen werden.")
    logging.info(f"Übertragung abgeschlossen: {success_count} von {len(orders)} Rechnungen erfolgreich übertragen.")

if __name__ == '__main__':
    main()