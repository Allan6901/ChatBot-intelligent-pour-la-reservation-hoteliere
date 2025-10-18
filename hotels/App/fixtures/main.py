import csv
from datetime import datetime, timedelta
import random

# --- 1. Hotels ---
hotels = [
    {"num_ho": 1, "nom_ho": "Hotel Paris", "rue_adr_ho": "Rue de Rivoli", "ville_ho": "Paris", "nb_etoiles_ho": 4},
    {"num_ho": 2, "nom_ho": "Hotel Nice", "rue_adr_ho": "Avenue des Fleurs", "ville_ho": "Nice", "nb_etoiles_ho": 5},
    {"num_ho": 3, "nom_ho": "Hotel Lyon", "rue_adr_ho": "Rue de la Gare", "ville_ho": "Lyon", "nb_etoiles_ho": 3},
    {"num_ho": 4, "nom_ho": "Hotel Marseille", "rue_adr_ho": "Boulevard Longchamp", "ville_ho": "Marseille", "nb_etoiles_ho": 4},
    {"num_ho": 5, "nom_ho": "Hotel Bordeaux", "rue_adr_ho": "Cours Victor Hugo", "ville_ho": "Bordeaux", "nb_etoiles_ho": 5},
]

with open("Hotel.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=hotels[0].keys())
    writer.writeheader()
    writer.writerows(hotels)

# --- 2. TypeChambre ---
types_chambre = [
    {"num_ty": 1, "nom_ty": "Simple", "prix_ty": 80.00},
    {"num_ty": 2, "nom_ty": "Double", "prix_ty": 120.00},
    {"num_ty": 3, "nom_ty": "Suite", "prix_ty": 200.00},
]

with open("TypeChambre.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=types_chambre[0].keys())
    writer.writeheader()
    writer.writerows(types_chambre)

# --- 3. Chambres ---
chambres = []
num_ch = 101
for h in hotels:
    for ty in types_chambre:
        for i in range(10):
            chambres.append({"num_ch": num_ch, "num_ho": h["num_ho"], "num_ty": ty["num_ty"]})
            num_ch += 1

with open("Chambre.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["num_ch", "num_ho", "num_ty"])
    writer.writeheader()
    writer.writerows(chambres)

# --- 4. Clients ---
clients = []
for i in range(1, 51):
    clients.append({
        "num_cl": i,
        "nom_cl": f"Nom{i}",
        "prenom_cl": f"Prenom{i}",
        "rue_adr_cl": f"{i} rue Exemple",
        "ville_cl": f"Ville{i % 5 + 1}"
    })

with open("Client.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=clients[0].keys())
    writer.writeheader()
    writer.writerows(clients)

# --- 5. Reservations et Occupations ---
reservations = []
occupations = []

# Stockage pour éviter chevauchements
occupations_by_chambre = {}  # {num_ch: [(date_a, date_d)]}
reservation_keys = set()     # {(num_cl, num_ho, num_ty, date_a)}

start_date = datetime(2025, 10, 1, 14, 0)

for client in clients:
    for _ in range(3):  # max 3 réservations par client
        hotel = random.choice(hotels)
        valid_types = list({c["num_ty"] for c in chambres if c["num_ho"] == hotel["num_ho"]})
        type_ch_num = random.choice(valid_types)
        valid_chambres = [c for c in chambres if c["num_ho"] == hotel["num_ho"] and c["num_ty"] == type_ch_num]
        random.shuffle(valid_chambres)

        nb_jours = random.randint(1, 5)
        assigned = False
        for chambre in valid_chambres:
            # Calculer la prochaine date disponible pour cette chambre
            last_end = max([d[1] for d in occupations_by_chambre.get(chambre["num_ch"], [])], default=start_date)
            date_a = last_end + timedelta(days=1)
            date_d = date_a + timedelta(days=nb_jours)

            # Vérifier qu’aucune occupation ne chevauche (C2)
            if all(date_d <= occ[0] or date_a >= occ[1] for occ in occupations_by_chambre.get(chambre["num_ch"], [])):
                reservations.append({
                    "num_cl": client["num_cl"],
                    "num_ho": hotel["num_ho"],
                    "num_ty": type_ch_num,
                    "date_a": date_a.strftime("%Y-%m-%d %H:%M:%S"),
                    "nb_jours": nb_jours,
                    "nb_chambres": 1
                })
                occupations.append({
                    "num_cl": client["num_cl"],
                    "num_ho": hotel["num_ho"],
                    "num_ch": chambre["num_ch"],
                    "date_a": date_a.strftime("%Y-%m-%d %H:%M:%S"),
                    "date_d": date_d.strftime("%Y-%m-%d %H:%M:%S")
                })
                occupations_by_chambre.setdefault(chambre["num_ch"], []).append((date_a, date_d))
                assigned = True
                break
        if not assigned:
            continue  # si aucune chambre dispo, on skip

# --- Écriture CSV ---
with open("Reservation.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["num_cl", "num_ho", "num_ty", "date_a", "nb_jours", "nb_chambres"])
    writer.writeheader()
    writer.writerows(reservations)

with open("Occupation.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["num_cl", "num_ho", "num_ch", "date_a", "date_d"])
    writer.writeheader()
    writer.writerows(occupations)

print("✅ Fichiers CSV générés correctement, sans chevauchement et respectant C1 et C2 !")
