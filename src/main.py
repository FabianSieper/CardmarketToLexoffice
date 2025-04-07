#!/usr/bin/env python
import logging
import time

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from csv_processor import take_cardmarket_orders_via_cmd_input
from lexoffice_api import create_invoice_payload, send_invoice_to_lexoffice
from utils import ask_or_get_api_key


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starte den Abgleich von CardMarket zu Lexoffice.")
    load_dotenv()
    api_key: str = ask_or_get_api_key()
    orders: pd.DataFrame = take_cardmarket_orders_via_cmd_input()

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
        time.sleep(0.5)
        
    logging.info(f"Übertragung abgeschlossen: {success_count} von {len(orders)} Rechnungen erfolgreich übertragen.")
    input("Drücken Sie Enter, um das Programm zu beenden.")

if __name__ == '__main__':
    main()