from django.contrib import admin
from .models import Hotel, TypeChambre, Chambre, Client, Reservation, Occupation

admin.site.register(Hotel)
admin.site.register(TypeChambre)
admin.site.register(Chambre)
admin.site.register(Client)
admin.site.register(Reservation)
admin.site.register(Occupation)
