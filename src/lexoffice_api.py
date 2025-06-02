import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd  # Added import for pd.Series type hint
import pytz

from utils import get_country_code, parse_date


def fix_encoding(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    try:
        return text.encode("latin1").decode("utf8")
    except Exception:
        return text

def create_invoice_payload(order: pd.Series) -> Optional[Dict[str, Any]]:
    customer_name: str = fix_encoding(order.get('name'))
    street: str = fix_encoding(order.get('street'))
    city_and_postal: str = fix_encoding(order.get('city'))
    country: str = fix_encoding(order.get('country'))
    if not all([customer_name, street, city_and_postal, country]):
        logging.error("Fehlende Kundendaten in shipment_nr: {}".format(order.get('shipment_nr', 'Unbekannt')))
        return None

    try:
        postal_code, city = city_and_postal.split(" ", 1)
    except ValueError:
        logging.error(f"Ungültiges Format für 'city': {city_and_postal}")
        return None
    country_code: str = get_country_code(country)

    customer: Dict[str, Any] = {
        "name": customer_name,
        "address": {
            "street": street,
            "zip": postal_code.strip(),
            "city": city.strip(),
            "countryCode": country_code
        }
    }

    unformatted_date: str = order.get('date of purchase')
    if not unformatted_date:
        logging.error("Kein Datum gefunden für shipment_nr: {}".format(order.get('shipment_nr', 'Unbekannt')))
        return None
    try:
        dt: datetime = parse_date(unformatted_date)
    except ValueError as e:
        logging.error(str(e))
        return None
    german_tz = pytz.timezone("Europe/Berlin")
    localized_dt = german_tz.localize(dt)
    voucher_date: str = localized_dt.isoformat(timespec='milliseconds')

    articles: List[Dict[str, Any]] = order.get('articles')
    if not articles:
        logging.error(f"Keine Artikel gefunden für shipment_nr: {order.get('shipment_nr', 'Unbekannt')}")
        return None

    line_items: List[Dict[str, Any]] = []
    for article in articles:
        unit_price_with_currency: str = article.get("price per card")
        name: str = fix_encoding(article.get("name"))
        quantity: int = article.get("quantity")
        card_condition: str = fix_encoding(article.get("card condition"))
        if not name or not unit_price_with_currency or not quantity:
            logging.error(f"Fehler bei Artikel in shipment_nr: {order.get('shipment_nr', 'Unbekannt')}")
            return None
        try:
            unit_price: Decimal = Decimal(unit_price_with_currency.split(" ")[0].replace(",", "."))
            currency: str = unit_price_with_currency.split(" ")[1]
        except Exception as e:
            logging.error(f"Preisformatierungsfehler: {e}")
            return None
        line_item = {
            "type": "custom",
            "name": name + (" (" + card_condition + ")" if card_condition else ""),
            "quantity": quantity,
            "unitName": "Stück",
            "unitPrice": {
                "currency": currency,
                "netAmount": str(unit_price),
                "taxRatePercentage": 0
            },
            "discountPercentage": 0,
            "lineItemAmount": str(unit_price * quantity)
        }
        line_items.append(line_item)

    shipping_cost_str: str = order.get("shipment costs")
    if shipping_cost_str:
        try:
            shipping_cost: Decimal = Decimal(shipping_cost_str.replace(",", "."))
        except Exception as e:
            logging.error(f"Fehler bei Versandkostenformatierung: {e}")
            return None
        shipping_item = {
            "type": "custom",
            "name": "Versandkosten",
            "quantity": 1,
            "unitName": "Pauschale",
            "unitPrice": {
                "currency": order.get("currency", "EUR"),
                "netAmount": str(shipping_cost),
                "taxRatePercentage": 0
            },
            "discountPercentage": 0,
            "lineItemAmount": str(shipping_cost)
        }
        line_items.append(shipping_item)
    else:
        logging.warning(f"Bestellung {order.get('shipment_nr', 'Unbekannt')} hat keine Versandkosten.")

    address: Dict[str, Any] = {
        "name": customer_name,
        "street": street,
        "zip": postal_code.strip(),
        "city": city.strip(),
        "countryCode": country_code
    }

    payload: Dict[str, Any] = {
        "customer": customer,
        "address": address,
        "totalPrice": {"currency": "EUR"},
        "shippingConditions": {
            "shippingDate": voucher_date,
            "shippingType": "none"
        },
        "archived": False,
        "voucherDate": voucher_date,
        "lineItems": line_items,
        "taxConditions": {"taxType": "vatfree"}
    }
    return payload

def send_invoice_to_lexoffice(invoice_payload: Dict[str, Any], api_key: str) -> bool:
    from requests import post
    LEXOFFICE_BASE_URL = "https://api.lexoffice.io/v1"
    endpoint = f"{LEXOFFICE_BASE_URL}/invoices"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = post(endpoint, json=invoice_payload, headers=headers)
        if response.status_code == 201:
            logging.info("Rechnung erfolgreich in Lexoffice angelegt.")
            return True
        else:
            logging.error(f"Fehler beim Anlegen der Rechnung: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Ausnahme beim Senden der Rechnung: {e}")
        return False