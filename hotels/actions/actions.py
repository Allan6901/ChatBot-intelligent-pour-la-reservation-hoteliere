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

        # Mapping direct des villes dans le texte - SOLUTION ROBUSTE
        ville_mapping = {
            'paris': 'Paris',
            'nice': 'Nice',
            'lyon': 'Lyon',
            'marseille': 'Marseille',
            'toulouse': 'Toulouse',
            'bordeaux': 'Bordeaux',
            'lille': 'Lille'
        }

        # 1. Essayer de récupérer depuis les entités
        entities = tracker.latest_message.get('entities', [])
        ville_entity = next((e for e in entities if e['entity'] == 'ville'), None)

        ville = None

        if ville_entity:
            ville = ville_entity['value']
        else:
            # 2. Fallback: chercher dans le texte du message
            message_text = tracker.latest_message.get('text', '').lower()

            for ville_key, ville_value in ville_mapping.items():
                if ville_key in message_text:
                    ville = ville_value
                    break

        # 3. Si toujours pas trouvé, utiliser le slot
        if not ville:
            ville = tracker.get_slot("ville")

        if not ville:
            dispatcher.utter_message(
                text="Veuillez préciser la ville parmi : Paris, Lyon, Marseille, Nice, Toulouse, Bordeaux ou Lille."
            )
            return []

        # Normaliser le nom de la ville
        ville = ville.capitalize()

        # Récupérer aussi le prix pour la requête
        prix_entity = next((e for e in entities if e['entity'] == 'prix'), None)
        prix_max = float(prix_entity['value']) if prix_entity else tracker.get_slot("prix")

        # Requête synchrone dans thread async
        def get_hotels_sync():
            qs = Hotel.objects.filter(ville_ho__iexact=ville).annotate(
                prix_moyen=Avg('chambre__num_ty__prix_ty')
            )
            if prix_max:
                qs = qs.filter(prix_moyen__lte=prix_max)
            return list(qs)

        hotels = await sync_to_async(get_hotels_sync)()

        if hotels:
            if prix_max:
                response = f"Voici les hôtels disponibles à {ville} avec un prix ≤ {prix_max}€ :\n"
            else:
                response = f"Voici les hôtels disponibles à {ville} :\n"

            for h in hotels:
                prix = h.prix_moyen or 0
                response += f"- {h.nom_ho} ({h.nb_etoiles_ho} étoiles) : prix moyen {prix:.2f}€\n"
        else:
            if prix_max:
                response = f"Désolé, aucun hôtel à {ville} ne correspond à votre budget de {prix_max}€."
            else:
                response = f"Désolé, aucun hôtel ne correspond à votre recherche à {ville}."

        dispatcher.utter_message(text=response)

        # Réinitialiser les slots
        return [SlotSet("ville", None), SlotSet("prix", None)]


class ActionRechercherParPrix(Action):
    def name(self):
        return "action_rechercher_par_prix"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):

        # Récupérer le prix depuis les entités
        entities = tracker.latest_message.get('entities', [])
        prix_entity = next((e for e in entities if e['entity'] == 'prix'), None)

        if prix_entity:
            prix_max = float(prix_entity['value'])
        else:
            # Fallback sur le slot
            prix_max = tracker.get_slot("prix")

        # Si pas de prix spécifié, utiliser un prix par défaut pour "pas cher"
        if not prix_max:
            # Analyser le texte pour les mots-clés "pas cher"
            message_text = tracker.latest_message.get('text', '').lower()

            mots_pas_chers = ['pas cher', 'pas chers', 'économique', 'bon marché', 'low cost', 'petit prix', 'bas prix']

            if any(mot in message_text for mot in mots_pas_chers):
                prix_max = 80  # Prix par défaut pour "pas cher"
                message_prix = f"Je vous montre les hôtels avec un prix moyen ≤ {prix_max}€ :"
            else:
                # Si pas de mots-clés "pas cher", demander le budget
                dispatcher.utter_message(text="Quel est votre budget maximum par nuit ?")
                return []
        else:
            message_prix = f"Voici les hôtels avec un prix moyen ≤ {prix_max}€ :"

        # Afficher le message approprié
        if 'message_prix' in locals():
            dispatcher.utter_message(text=message_prix)

        # Requête pour les hôtels par prix
        def get_hotels_par_prix_sync():
            qs = Hotel.objects.annotate(
                prix_moyen=Avg('chambre__num_ty__prix_ty')
            ).filter(prix_moyen__lte=prix_max).order_by('prix_moyen')
            return list(qs)

        hotels = await sync_to_async(get_hotels_par_prix_sync)()

        if hotels:
            response = ""
            for h in hotels:
                prix = h.prix_moyen or 0
                response += f"- {h.nom_ho} à {h.ville_ho} ({h.nb_etoiles_ho} étoiles) : {prix:.2f}€\n"
        else:
            response = f"Désolé, aucun hôtel ne correspond à votre budget de {prix_max}€."

        dispatcher.utter_message(text=response)
        return [SlotSet("prix", None)]


class ActionRechercherParCapacite(Action):
    def name(self):
        return "action_rechercher_par_capacite"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):

        # Récupérer le nombre de personnes
        entities = tracker.latest_message.get('entities', [])
        personnes_entity = next((e for e in entities if e['entity'] == 'personnes'), None)

        if personnes_entity:
            personnes = personnes_entity['value']
        else:
            personnes = tracker.get_slot("personnes")

        if not personnes:
            dispatcher.utter_message(text="Pour combien de personnes souhaitez-vous réserver ?")
            return []

        # Mapping texte → nombre
        mapping_personnes = {
            'une': '1', 'un': '1',
            'deux': '2',
            'trois': '3',
            'quatre': '4',
            'cinq': '5'
        }

        nb_personnes = mapping_personnes.get(personnes.lower(), personnes)

        dispatcher.utter_message(
            text=f"Je vais rechercher des hôtels pour {nb_personnes} personne(s). "
                 f"Cette fonctionnalité est en cours de développement. "
                 f"En attendant, vous pouvez me donner une ville pour affiner votre recherche."
        )
        return [SlotSet("personnes", nb_personnes)]


class ActionDemanderVille(Action):
    def name(self):
        return "action_demander_ville"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):
        dispatcher.utter_message(text="Dans quelle ville souhaitez-vous rechercher un hôtel ?")
        return []