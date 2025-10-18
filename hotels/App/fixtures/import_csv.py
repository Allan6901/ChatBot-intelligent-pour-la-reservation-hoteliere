import csv
from datetime import datetime
from django.db import transaction, IntegrityError
from django.utils.timezone import make_aware
import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings")
django.setup()

from App.models import Hotel, TypeChambre, Chambre, Client, Reservation, Occupation

def import_hotels():
    with open("Hotel.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            Hotel.objects.create(
                num_ho=int(row["num_ho"]),
                nom_ho=row["nom_ho"],
                rue_adr_ho=row["rue_adr_ho"],
                ville_ho=row["ville_ho"],
                nb_etoiles_ho=int(row["nb_etoiles_ho"])
            )

def import_types():
    with open("TypeChambre.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            TypeChambre.objects.create(
                num_ty=int(row["num_ty"]),
                nom_ty=row["nom_ty"],
                prix_ty=float(row["prix_ty"])
            )

def import_chambres():
    with open("Chambre.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            Chambre.objects.create(
                num_ch=int(row["num_ch"]),
                num_ho_id=int(row["num_ho"]),
                num_ty_id=int(row["num_ty"])
            )

def import_clients():
    with open("Client.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            Client.objects.create(
                num_cl=int(row["num_cl"]),
                nom_cl=row["nom_cl"],
                prenom_cl=row["prenom_cl"],
                rue_adr_cl=row["rue_adr_cl"],
                ville_cl=row["ville_cl"]
            )

def import_reservations():
    with open("Reservation.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_a = make_aware(datetime.strptime(row["date_a"], "%Y-%m-%d %H:%M:%S"))
            try:
                with transaction.atomic():
                    Reservation.objects.create(
                        num_cl_id=int(row["num_cl"]),
                        num_ho_id=int(row["num_ho"]),
                        num_ty_id=int(row["num_ty"]),
                        date_a=date_a,
                        nb_jours=int(row["nb_jours"]),
                        nb_chambres=int(row["nb_chambres"])
                    )
            except IntegrityError as e:
                print("Erreur Reservation :", e)

def import_occupations():
    with open("Occupation.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_a = make_aware(datetime.strptime(row["date_a"], "%Y-%m-%d %H:%M:%S"))
            date_d = make_aware(datetime.strptime(row["date_d"], "%Y-%m-%d %H:%M:%S"))
            try:
                with transaction.atomic():
                    Occupation.objects.create(
                        num_cl_id=int(row["num_cl"]),
                        num_ho_id=int(row["num_ho"]),
                        num_ch_id=int(row["num_ch"]),
                        date_a=date_a,
                        date_d=date_d
                    )
            except IntegrityError as e:
                print("Erreur Occupation :", e)

if __name__ == "__main__":
    if __name__ == "__main__":
        # Vider les tables avant import
        Occupation.objects.all().delete()
        Reservation.objects.all().delete()
        Client.objects.all().delete()
        Chambre.objects.all().delete()
        TypeChambre.objects.all().delete()
        Hotel.objects.all().delete()

        # Importer
        import_hotels()
        import_types()
        import_chambres()
        import_clients()
        import_reservations()
        import_occupations()
        print("Import CSV terminé !")

