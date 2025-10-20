import os
import sys
import django
from django.db.models import Avg
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from asgiref.sync import sync_to_async
from rasa_sdk.events import SlotSet, FollowupAction

# Ajouter le projet Django au PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings")
django.setup()

from App.models import Hotel


class ActionRechercherHotel(Action):
    def name(self):
        return "action_rechercher_hotel"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):

        # Liste des villes connues pour le fallback
        villes_connues = ['paris', 'lyon', 'marseille', 'nice', 'toulouse', 'bordeaux', 'lille']

        # 1. Essayer de récupérer depuis les entités
        entities = tracker.latest_message.get('entities', [])
        ville_entity = next((e for e in entities if e['entity'] == 'ville'), None)

        ville = None

        if ville_entity:
            ville = ville_entity['value']
        else:
            # 2. Fallback: chercher dans le texte du message
            message_text = tracker.latest_message.get('text', '').lower()
            for ville_candidate in villes_connues:
                if ville_candidate in message_text:
                    ville = ville_candidate.capitalize()
                    break

        # 3. Si toujours pas trouvé, utiliser le slot
        if not ville:
            ville = tracker.get_slot("ville")

        if not ville:
            dispatcher.utter_message(text="Veuillez préciser la ville (par exemple : Paris, Lyon, Nice, etc.).")
            return [FollowupAction("utter_demander_ville")]

        # Normaliser le nom de la ville
        ville = ville.capitalize()

        # Requête synchrone dans thread async
        def get_hotels_sync():
            qs = Hotel.objects.filter(ville_ho__iexact=ville).annotate(
                prix_moyen=Avg('chambre__num_ty__prix_ty')
            )
            prix_max = tracker.get_slot("prix")
            if prix_max:
                qs = qs.filter(prix_moyen__lte=prix_max)
            return list(qs)

        hotels = await sync_to_async(get_hotels_sync)()

        if hotels:
            response = f"Voici les hôtels disponibles à {ville} :\n"
            for h in hotels:
                prix = h.prix_moyen or 0
                response += f"- {h.nom_ho} ({h.nb_etoiles_ho} étoiles) : prix moyen {prix:.2f}€\n"
        else:
            response = f"Désolé, aucun hôtel ne correspond à votre recherche à {ville}."

        dispatcher.utter_message(text=response)

        # Réinitialiser les slots
        return [SlotSet("ville", None), SlotSet("prix", None)]


class ActionDemanderVille(Action):
    def name(self):
        return "action_demander_ville"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):
        dispatcher.utter_message(text="Dans quelle ville souhaitez-vous rechercher un hôtel ?")
        return []