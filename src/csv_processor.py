import logging
import os
import sys
from typing import Any, Dict, List

import pandas as pd

from utils import extract_quantity_and_name


def extract_csv_data(file_path: str) -> pd.DataFrame:
    ext: str = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        try:
            df = pd.read_csv(file_path, encoding='utf-8', sep=';')
        except pd.errors.ParserError:
            print("Fehler beim Einlesen der CSV-Datei. Es wird nun versucht die Datei mit ',' als Separator zu laden..")
            df = pd.read_csv(file_path, encoding='utf-8', sep=',')
    else:
        logging.error("Unsupported file type: " + ext)
        sys.exit(1)
    df.columns = df.columns.str.strip().str.lower()
    return df

def parse_articles(d: str, p: str, n: str) -> List[Dict[str, Any]]:
    d_items = [item.strip() for item in d.split(" | ")]
    p_items = [item.strip() for item in p.split(" | ")]
    n_items = [item.strip() for item in n.split(" | ")]

    if not (len(d_items) == len(p_items) == len(n_items)):
        raise ValueError("Mismatch in number of items between description, product id, and localized product name.")

    articles = []
    for d_item, p_item, n_item in zip(d_items, p_items, n_items):
        parts = d_item.split(" - ")
        result = extract_quantity_and_name(parts[0].strip()) if parts and parts[0].strip() else None
        quantity, description = (None, None)
        if result:
            quantity, description = result
        article = {
            "description": description,
            "quantity": quantity,
            "number": parts[1].strip() if len(parts) > 1 else None,
            "rarity": parts[2].strip() if len(parts) > 2 else None,
            "card condition": parts[3].strip() if len(parts) > 3 else None,
            "language": parts[4].strip() if len(parts) > 4 else None,
            "price per card": parts[-1].strip() if len(parts) > 5 else None,
            "product id": p_item,
            "name": n_item
        }
        articles.append(article)
    return articles

def join_shipment_data(orders: pd.DataFrame) -> pd.DataFrame:
    if 'orderid' not in orders.columns:
        logging.error("Spalte 'orderid' wurde in den Daten nicht gefunden.")
        return pd.DataFrame()
    
    orders['group'] = orders['orderid'].notna().cumsum()
    list_cols = ['description', 'product id', 'localized product name']
    agg_dict = {col: (lambda x: list(x)) for col in list_cols}
    for col in orders.columns:
        if col not in list_cols + ['group']:
            agg_dict[col] = 'first'
    shipments = orders.groupby('group', sort=False).agg(agg_dict).reset_index(drop=True)
    shipments['orderid'] = shipments['orderid'].astype(int)
    shipments['articles'] = shipments.apply(
        lambda row: [item for sublist in [parse_articles(d, p, n) for d, p, n in zip(row["description"], row["product id"], row["localized product name"])] for item in sublist],
        axis=1
    )
    shipments.drop(columns=list_cols, inplace=True)
    return shipments

def take_cardmarket_orders_via_cmd_input() -> pd.DataFrame:
    while True:
        order_csv_path: str = input("Bitte den Pfad zur CSV-Datei mit den Bestellungen angeben: ").strip("\"'")
        if not order_csv_path.endswith(".csv"):
            logging.error("Bitte eine CSV-Datei angeben.")
            continue
        if not os.path.isfile(order_csv_path):
            logging.error(f"Die Datei {order_csv_path} existiert nicht.")
            continue
        orders = extract_csv_data(order_csv_path)
        if orders.empty:
            logging.error("Keine Bestellungen gefunden.")
            continue
        joined_orders = join_shipment_data(orders)
        if joined_orders.empty:
            logging.error("Keine Bestellungen nach dem Zusammenfügen von Bestellungen gefunden.")
            continue
        return joined_orders