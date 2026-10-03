"""
generate_sql_data.py
---------------------
Builds the structured (SQLite) side of the world: shipments moving along
routes, inventory levels at factories, and disruption events.

Tables:
  shipments(id, supplier_id, route_from, route_to, factory_id, product_id,
            departure_date, expected_arrival, actual_arrival, status,
            cost_usd, units)
  inventory(factory_id, product_id, date, units_on_hand, days_of_cover)
  disruption_events(id, entity_type, entity_id, disruption_type,
                     start_date, duration_days, severity)
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.schema import (
    SUPPLIERS, PORTS, FACTORIES, PRODUCTS, ROUTES, DISRUPTION_TYPES,
    SUPPLIER_TO_PORT, SUPPLIER_TO_FACTORIES, FACTORY_TO_PRODUCTS,
)

DB_PATH = Path(__file__).parent / "nexus.db"


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS shipments;
        DROP TABLE IF EXISTS inventory;
        DROP TABLE IF EXISTS disruption_events;

        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT NOT NULL,
            route_from TEXT NOT NULL,
            route_to TEXT NOT NULL,
            factory_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            expected_arrival TEXT NOT NULL,
            actual_arrival TEXT,
            status TEXT NOT NULL,
            delay_days INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL,
            units INTEGER NOT NULL
        );

        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factory_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            date TEXT NOT NULL,
            units_on_hand INTEGER NOT NULL,
            days_of_cover REAL NOT NULL
        );

        CREATE TABLE disruption_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            disruption_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            severity TEXT NOT NULL
        );

        CREATE INDEX idx_shipments_supplier ON shipments(supplier_id);
        CREATE INDEX idx_shipments_status ON shipments(status);
        CREATE INDEX idx_disruption_entity ON disruption_events(entity_id);
        """
    )


def generate(days: int = 90, n_disruptions: int = 12) -> None:
    random.seed(42)  # inside generate() so repeated calls are deterministic
    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)

    start = date.today() - timedelta(days=days)
    shipment_rows = []

    for sid in [s[0] for s in SUPPLIERS]:
        origin_port = SUPPLIER_TO_PORT[sid]
        factories = SUPPLIER_TO_FACTORIES[sid]

        for day_offset in range(0, days, 5):
            departure = start + timedelta(days=day_offset)
            factory_id = random.choice(factories)

            possible_routes = [
                (f, t, mode, d) for (f, t, mode, d) in ROUTES if f == origin_port
            ]
            if not possible_routes:
                continue
            route_from, route_to, mode, transit_days = random.choice(possible_routes)

            expected_arrival = departure + timedelta(days=transit_days)
            is_delayed = random.random() < 0.15
            delay_days = random.randint(2, 10) if is_delayed else 0
            actual_arrival = expected_arrival + timedelta(days=delay_days)
            status = "delayed" if is_delayed else "on_time"
            if actual_arrival > date.today():
                status = "in_transit"
                actual_arrival = None

            product_id = random.choice(FACTORY_TO_PRODUCTS[factory_id])
            units = random.randint(5000, 50000)
            cost_usd = round(units * random.uniform(0.8, 3.5), 2)

            shipment_rows.append(
                [
                    sid, route_from, route_to, factory_id, product_id,
                    departure.isoformat(), expected_arrival.isoformat(),
                    actual_arrival.isoformat() if actual_arrival else None,
                    status, delay_days, cost_usd, units,
                ]
            )

    conn.executemany(
        """INSERT INTO shipments
           (supplier_id, route_from, route_to, factory_id, product_id,
            departure_date, expected_arrival, actual_arrival, status,
            delay_days, cost_usd, units)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        shipment_rows,
    )

    inventory_rows = []
    for fid, product_list in FACTORY_TO_PRODUCTS.items():
        for product_id in product_list:
            baseline_units = random.randint(8000, 30000)
            for week in range(0, days, 7):
                snapshot_date = start + timedelta(days=week)
                drift = random.randint(-3000, 3000)
                units = max(baseline_units + drift, 500)
                daily_burn = random.uniform(300, 900)
                days_of_cover = round(units / daily_burn, 1)
                inventory_rows.append(
                    [fid, product_id, snapshot_date.isoformat(), units, days_of_cover]
                )

    conn.executemany(
        """INSERT INTO inventory (factory_id, product_id, date, units_on_hand, days_of_cover)
           VALUES (?, ?, ?, ?, ?)""",
        inventory_rows,
    )

    disruption_rows = []
    entity_pool = (
        [("Port", p[0]) for p in PORTS]
        + [("Supplier", s[0]) for s in SUPPLIERS]
        + [("Factory", f[0]) for f in FACTORIES]
    )
    for _ in range(n_disruptions):
        entity_type, entity_id = random.choice(entity_pool)
        disruption_type = random.choice(DISRUPTION_TYPES)
        start_date = start + timedelta(days=random.randint(0, days - 10))
        duration = random.randint(2, 14)
        severity = random.choices(["low", "medium", "high"], weights=[0.4, 0.4, 0.2])[0]
        disruption_rows.append(
            [entity_type, entity_id, disruption_type, start_date.isoformat(), duration, severity]
        )

    conn.executemany(
        """INSERT INTO disruption_events
           (entity_type, entity_id, disruption_type, start_date, duration_days, severity)
           VALUES (?, ?, ?, ?, ?, ?)""",
        disruption_rows,
    )

    conn.commit()
    print(f"Generated {len(shipment_rows)} shipments, {len(inventory_rows)} inventory "
          f"snapshots, {len(disruption_rows)} disruption events into {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    generate()
