// NEXUS supply chain graph -- generated, do not hand-edit

// Constraints (run once)
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Supplier) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Port) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Factory) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Product) REQUIRE n.id IS UNIQUE;

// Nodes
MERGE (:Supplier {id: "SUP-TSMC-HC", name: "TSMC Hsinchu Fab", country: "Taiwan", category: "semiconductor"});
MERGE (:Supplier {id: "SUP-UMC-TN", name: "UMC Tainan Fab", country: "Taiwan", category: "semiconductor"});
MERGE (:Supplier {id: "SUP-SAMSUNG-HW", name: "Samsung Hwaseong Fab", country: "South Korea", category: "semiconductor"});
MERGE (:Supplier {id: "SUP-GLOBALF-SG", name: "GlobalFoundries Singapore", country: "Singapore", category: "semiconductor"});
MERGE (:Supplier {id: "SUP-INFINEON-KL", name: "Infineon Kulim", country: "Malaysia", category: "power_components"});
MERGE (:Supplier {id: "SUP-MURATA-VN", name: "Murata Vietnam Plant", country: "Vietnam", category: "passive_components"});
MERGE (:Port {id: "PORT-KEELUNG", name: "Keelung", country: "Taiwan"});
MERGE (:Port {id: "PORT-BUSAN", name: "Busan", country: "South Korea"});
MERGE (:Port {id: "PORT-SINGAPORE", name: "Singapore", country: "Singapore"});
MERGE (:Port {id: "PORT-YOKOHAMA", name: "Yokohama", country: "Japan"});
MERGE (:Port {id: "PORT-HAMBURG", name: "Hamburg", country: "Germany"});
MERGE (:Port {id: "PORT-ROTTERDAM", name: "Rotterdam", country: "Netherlands"});
MERGE (:Factory {id: "FAC-SONY-KUMAMOTO", name: "Sony Kumamoto Assembly", country: "Japan"});
MERGE (:Factory {id: "FAC-DENSO-NAGOYA", name: "Denso Nagoya Plant", country: "Japan"});
MERGE (:Factory {id: "FAC-BOSCH-STUTTGART", name: "Bosch Stuttgart Plant", country: "Germany"});
MERGE (:Factory {id: "FAC-PHILIPS-EINDHOVEN", name: "Philips Eindhoven Plant", country: "Netherlands"});
MERGE (:Product {id: "PROD-SENSOR-X1", name: "Automotive Sensor X1"});
MERGE (:Product {id: "PROD-CAMERA-M4", name: "Camera Module M4"});
MERGE (:Product {id: "PROD-POWER-CTRL", name: "EV Power Controller"});
MERGE (:Product {id: "PROD-DISPLAY-D2", name: "Display Driver D2"});

// Edges
MATCH (a {id: "SUP-TSMC-HC"}), (b {id: "PORT-KEELUNG"}) MERGE (a)-[:SHIPS_FROM]->(b);
MATCH (a {id: "SUP-UMC-TN"}), (b {id: "PORT-KEELUNG"}) MERGE (a)-[:SHIPS_FROM]->(b);
MATCH (a {id: "SUP-SAMSUNG-HW"}), (b {id: "PORT-BUSAN"}) MERGE (a)-[:SHIPS_FROM]->(b);
MATCH (a {id: "SUP-GLOBALF-SG"}), (b {id: "PORT-SINGAPORE"}) MERGE (a)-[:SHIPS_FROM]->(b);
MATCH (a {id: "SUP-INFINEON-KL"}), (b {id: "PORT-SINGAPORE"}) MERGE (a)-[:SHIPS_FROM]->(b);
MATCH (a {id: "SUP-MURATA-VN"}), (b {id: "PORT-SINGAPORE"}) MERGE (a)-[:SHIPS_FROM]->(b);
MATCH (a {id: "PORT-KEELUNG"}), (b {id: "PORT-YOKOHAMA"}) MERGE (a)-[:ROUTE_TO {mode: "sea", days: 4}]->(b);
MATCH (a {id: "PORT-BUSAN"}), (b {id: "PORT-YOKOHAMA"}) MERGE (a)-[:ROUTE_TO {mode: "sea", days: 2}]->(b);
MATCH (a {id: "PORT-SINGAPORE"}), (b {id: "PORT-YOKOHAMA"}) MERGE (a)-[:ROUTE_TO {mode: "sea", days: 6}]->(b);
MATCH (a {id: "PORT-KEELUNG"}), (b {id: "PORT-HAMBURG"}) MERGE (a)-[:ROUTE_TO {mode: "sea", days: 28}]->(b);
MATCH (a {id: "PORT-SINGAPORE"}), (b {id: "PORT-ROTTERDAM"}) MERGE (a)-[:ROUTE_TO {mode: "sea", days: 24}]->(b);
MATCH (a {id: "PORT-BUSAN"}), (b {id: "PORT-ROTTERDAM"}) MERGE (a)-[:ROUTE_TO {mode: "sea", days: 30}]->(b);
MATCH (a {id: "PORT-YOKOHAMA"}), (b {id: "FAC-SONY-KUMAMOTO"}) MERGE (a)-[:SUPPLIES]->(b);
MATCH (a {id: "PORT-YOKOHAMA"}), (b {id: "FAC-DENSO-NAGOYA"}) MERGE (a)-[:SUPPLIES]->(b);
MATCH (a {id: "PORT-HAMBURG"}), (b {id: "FAC-BOSCH-STUTTGART"}) MERGE (a)-[:SUPPLIES]->(b);
MATCH (a {id: "PORT-ROTTERDAM"}), (b {id: "FAC-PHILIPS-EINDHOVEN"}) MERGE (a)-[:SUPPLIES]->(b);
MATCH (a {id: "SUP-TSMC-HC"}), (b {id: "FAC-SONY-KUMAMOTO"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-TSMC-HC"}), (b {id: "FAC-DENSO-NAGOYA"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-TSMC-HC"}), (b {id: "FAC-BOSCH-STUTTGART"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-UMC-TN"}), (b {id: "FAC-SONY-KUMAMOTO"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-SAMSUNG-HW"}), (b {id: "FAC-DENSO-NAGOYA"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-SAMSUNG-HW"}), (b {id: "FAC-PHILIPS-EINDHOVEN"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-GLOBALF-SG"}), (b {id: "FAC-BOSCH-STUTTGART"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-INFINEON-KL"}), (b {id: "FAC-BOSCH-STUTTGART"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-INFINEON-KL"}), (b {id: "FAC-PHILIPS-EINDHOVEN"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-MURATA-VN"}), (b {id: "FAC-SONY-KUMAMOTO"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "SUP-MURATA-VN"}), (b {id: "FAC-DENSO-NAGOYA"}) MERGE (a)-[:FEEDS]->(b);
MATCH (a {id: "FAC-SONY-KUMAMOTO"}), (b {id: "PROD-CAMERA-M4"}) MERGE (a)-[:PRODUCES]->(b);
MATCH (a {id: "FAC-DENSO-NAGOYA"}), (b {id: "PROD-SENSOR-X1"}) MERGE (a)-[:PRODUCES]->(b);
MATCH (a {id: "FAC-BOSCH-STUTTGART"}), (b {id: "PROD-POWER-CTRL"}) MERGE (a)-[:PRODUCES]->(b);
MATCH (a {id: "FAC-PHILIPS-EINDHOVEN"}), (b {id: "PROD-DISPLAY-D2"}) MERGE (a)-[:PRODUCES]->(b);