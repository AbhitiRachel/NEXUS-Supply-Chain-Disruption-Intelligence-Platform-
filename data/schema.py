"""
schema.py
---------
Single source of truth for the synthetic supply chain world that NEXUS
operates on. Every data generator (graph, SQL, documents) imports these
constants so an entity like "Taiwan Semiconductor Fab" means the same
thing everywhere -- the graph, the shipment records, and the documents
all refer to the same named suppliers, ports, and factories.

Domain: a simplified electronics supply chain -- chips move from
fabrication plants (mostly Taiwan/Southeast Asia) through ports to
assembly factories (Japan, Europe) that build finished products.
"""

import random

random.seed(42)  # reproducibility -- matters for evaluation ground truth

# --- Entities -------------------------------------------------------------

SUPPLIERS = [
    ("SUP-TSMC-HC", "TSMC Hsinchu Fab", "Taiwan", "semiconductor"),
    ("SUP-UMC-TN", "UMC Tainan Fab", "Taiwan", "semiconductor"),
    ("SUP-SAMSUNG-HW", "Samsung Hwaseong Fab", "South Korea", "semiconductor"),
    ("SUP-GLOBALF-SG", "GlobalFoundries Singapore", "Singapore", "semiconductor"),
    ("SUP-INFINEON-KL", "Infineon Kulim", "Malaysia", "power_components"),
    ("SUP-MURATA-VN", "Murata Vietnam Plant", "Vietnam", "passive_components"),
]

PORTS = [
    ("PORT-KEELUNG", "Keelung", "Taiwan"),
    ("PORT-BUSAN", "Busan", "South Korea"),
    ("PORT-SINGAPORE", "Singapore", "Singapore"),
    ("PORT-YOKOHAMA", "Yokohama", "Japan"),
    ("PORT-HAMBURG", "Hamburg", "Germany"),
    ("PORT-ROTTERDAM", "Rotterdam", "Netherlands"),
]

FACTORIES = [
    ("FAC-SONY-KUMAMOTO", "Sony Kumamoto Assembly", "Japan"),
    ("FAC-DENSO-NAGOYA", "Denso Nagoya Plant", "Japan"),
    ("FAC-BOSCH-STUTTGART", "Bosch Stuttgart Plant", "Germany"),
    ("FAC-PHILIPS-EINDHOVEN", "Philips Eindhoven Plant", "Netherlands"),
]

PRODUCTS = [
    ("PROD-SENSOR-X1", "Automotive Sensor X1"),
    ("PROD-CAMERA-M4", "Camera Module M4"),
    ("PROD-POWER-CTRL", "EV Power Controller"),
    ("PROD-DISPLAY-D2", "Display Driver D2"),
]

ROUTES = [
    # (from_port, to_port, mode, typical_days)
    ("PORT-KEELUNG", "PORT-YOKOHAMA", "sea", 4),
    ("PORT-BUSAN", "PORT-YOKOHAMA", "sea", 2),
    ("PORT-SINGAPORE", "PORT-YOKOHAMA", "sea", 6),
    ("PORT-KEELUNG", "PORT-HAMBURG", "sea", 28),
    ("PORT-SINGAPORE", "PORT-ROTTERDAM", "sea", 24),
    ("PORT-BUSAN", "PORT-ROTTERDAM", "sea", 30),
]

DISRUPTION_TYPES = [
    "port_strike",
    "factory_shutdown",
    "typhoon_closure",
    "customs_delay",
    "geopolitical_restriction",
]

# --- Relationships (defines the supply chain graph structure) -------------
# supplier -> nearest_port -> [route] -> destination_port -> factory -> product
SUPPLIER_TO_PORT = {
    "SUP-TSMC-HC": "PORT-KEELUNG",
    "SUP-UMC-TN": "PORT-KEELUNG",
    "SUP-SAMSUNG-HW": "PORT-BUSAN",
    "SUP-GLOBALF-SG": "PORT-SINGAPORE",
    "SUP-INFINEON-KL": "PORT-SINGAPORE",
    "SUP-MURATA-VN": "PORT-SINGAPORE",
}

PORT_TO_FACTORY = {
    "PORT-YOKOHAMA": ["FAC-SONY-KUMAMOTO", "FAC-DENSO-NAGOYA"],
    "PORT-HAMBURG": ["FAC-BOSCH-STUTTGART"],
    "PORT-ROTTERDAM": ["FAC-PHILIPS-EINDHOVEN"],
}

FACTORY_TO_PRODUCTS = {
    "FAC-SONY-KUMAMOTO": ["PROD-CAMERA-M4"],
    "FAC-DENSO-NAGOYA": ["PROD-SENSOR-X1"],
    "FAC-BOSCH-STUTTGART": ["PROD-POWER-CTRL"],
    "FAC-PHILIPS-EINDHOVEN": ["PROD-DISPLAY-D2"],
}

# Which suppliers feed which factories (a supplier may feed more than one)
SUPPLIER_TO_FACTORIES = {
    "SUP-TSMC-HC": ["FAC-SONY-KUMAMOTO", "FAC-DENSO-NAGOYA", "FAC-BOSCH-STUTTGART"],
    "SUP-UMC-TN": ["FAC-SONY-KUMAMOTO"],
    "SUP-SAMSUNG-HW": ["FAC-DENSO-NAGOYA", "FAC-PHILIPS-EINDHOVEN"],
    "SUP-GLOBALF-SG": ["FAC-BOSCH-STUTTGART"],
    "SUP-INFINEON-KL": ["FAC-BOSCH-STUTTGART", "FAC-PHILIPS-EINDHOVEN"],
    "SUP-MURATA-VN": ["FAC-SONY-KUMAMOTO", "FAC-DENSO-NAGOYA"],
}


def all_supplier_ids():
    return [s[0] for s in SUPPLIERS]


def all_port_ids():
    return [p[0] for p in PORTS]


def all_factory_ids():
    return [f[0] for f in FACTORIES]


def all_product_ids():
    return [p[0] for p in PRODUCTS]
