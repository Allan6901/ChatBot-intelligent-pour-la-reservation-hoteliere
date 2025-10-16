from django.db import models

class Hotel(models.Model):
    num_ho = models.AutoField(primary_key=True)
    nom_ho = models.CharField(max_length=100)
    rue_adr_ho = models.CharField(max_length=100)
    ville_ho = models.CharField(max_length=100)
    nb_etoiles_ho = models.IntegerField()

    def __str__(self):
        return self.nom_ho


class TypeChambre(models.Model):
    num_ty = models.AutoField(primary_key=True)
    nom_ty = models.CharField(max_length=100)
    prix_ty = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nom_ty


class Chambre(models.Model):
    num_ch = models.IntegerField()
    num_ho = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    num_ty = models.ForeignKey(TypeChambre, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('num_ch', 'num_ho'),)

    def __str__(self):
        return f"Chambre {self.num_ch} ({self.num_ho.nom_ho})"


class Client(models.Model):
    num_cl = models.AutoField(primary_key=True)
    nom_cl = models.CharField(max_length=100)
    prenom_cl = models.CharField(max_length=100)
    rue_adr_cl = models.CharField(max_length=100)
    ville_cl = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.prenom_cl} {self.nom_cl}"


class Reservation(models.Model):
    num_cl = models.ForeignKey(Client, on_delete=models.CASCADE)
    num_ho = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    num_ty = models.ForeignKey(TypeChambre, on_delete=models.CASCADE)
    date_a = models.DateTimeField()
    nb_jours = models.IntegerField()
    nb_chambres = models.IntegerField()

    class Meta:
        unique_together = (('num_cl', 'num_ho', 'num_ty', 'date_a'),)

    def __str__(self):
        return f"Réservation {self.num_cl} à {self.num_ho} le {self.date_a}"


class Occupation(models.Model):
    num_cl = models.ForeignKey(Client, on_delete=models.CASCADE)
    num_ho = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    num_ch = models.ForeignKey(Chambre, on_delete=models.CASCADE)
    date_a = models.DateTimeField()
    date_d = models.DateTimeField()

    class Meta:
        unique_together = (('num_cl', 'num_ho', 'num_ch', 'date_a'),)

    def __str__(self):
        return f"Occupation {self.num_ch} du {self.date_a} au {self.date_d}"
