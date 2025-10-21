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

        # Mapping direct des villes dans le texte
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

        # DÉTECTION INTELLIGENTE : Si pas de ville mais demande de capacité, rediriger
        if not ville:
            message_text = tracker.latest_message.get('text', '').lower()

            # Mots-clés pour détecter les demandes de capacité
            mots_capacite = [
                'personne', 'personnes', 'adulte', 'adultes', 'voyageur', 'voyageurs',
                'seul', 'couple', 'groupe', 'famille', 'familial', 'familiale',
                'simple', 'double', 'triple', 'suite'
            ]

            if any(mot in message_text for mot in mots_capacite):
                # C'est une demande de capacité, rediriger vers l'action appropriée
                from rasa_sdk.events import FollowupAction
                return [FollowupAction("action_rechercher_par_capacite")]

        if not ville:
            dispatcher.utter_message(
                text="Veuillez préciser la ville parmi : Paris, Lyon, Marseille, Nice, Toulouse, Bordeaux ou Lille."
            )
            return []

        # Normaliser le nom de la ville
        ville = ville.capitalize()

        # Récupérer aussi le prix et le nombre de personnes
        prix_entity = next((e for e in entities if e['entity'] == 'prix'), None)
        personnes_entity = next((e for e in entities if e['entity'] == 'personnes'), None)

        prix_max = float(prix_entity['value']) if prix_entity else tracker.get_slot("prix")
        personnes = personnes_entity['value'] if personnes_entity else tracker.get_slot("personnes")

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
            # Construire le message en fonction des critères
            if prix_max and personnes:
                response = f"Voici les hôtels à {ville} pour {personnes} personne(s) avec prix ≤ {prix_max}€ :\n"
            elif prix_max:
                response = f"Voici les hôtels à {ville} avec prix ≤ {prix_max}€ :\n"
            elif personnes:
                response = f"Voici les hôtels à {ville} pour {personnes} personne(s) :\n"
            else:
                response = f"Voici les hôtels disponibles à {ville} :\n"

            for h in hotels:
                prix = h.prix_moyen or 0
                response += f"- {h.nom_ho} ({h.nb_etoiles_ho} étoiles) : prix moyen {prix:.2f}€\n"

        else:
            response = f"Désolé, aucun hôtel ne correspond à votre recherche à {ville}."
            if prix_max:
                response += f" avec budget de {prix_max}€"
            if personnes:
                response += f" pour {personnes} personne(s)"

        dispatcher.utter_message(text=response)

        # Réinitialiser les slots
        return [SlotSet("ville", None), SlotSet("prix", None), SlotSet("personnes", None)]

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
            'une': '1', 'un': '1', 'seul': '1', 'simple': '1',
            'deux': '2', 'couple': '2', 'double': '2',
            'trois': '3', 'triple': '3',
            'quatre': '4', 'familiale': '4', 'famille': '4',
            'cinq': '5'
        }

        nb_personnes = mapping_personnes.get(personnes.lower(), personnes)

        # Types de chambres recommandées
        types_chambres = {
            '1': 'chambre simple',
            '2': 'chambre double',
            '3': 'chambre triple',
            '4': 'chambre familiale',
            '5': 'suite familiale'
        }

        type_chambre = types_chambres.get(nb_personnes, f"chambre pour {nb_personnes} personnes")

        # Rechercher tous les hôtels (pour l'instant)
        def get_hotels_sync():
            qs = Hotel.objects.annotate(
                prix_moyen=Avg('chambre__num_ty__prix_ty')
            )
            return list(qs)

        hotels = await sync_to_async(get_hotels_sync)()

        if hotels:
            response = f"🛌 Pour {nb_personnes} personne(s), je vous recommande une **{type_chambre}**.\n\n"
            response += f"🏨 **Hôtels disponibles :**\n"

            for h in hotels:
                prix = h.prix_moyen or 0
                response += f"- {h.nom_ho} à {h.ville_ho} ({h.nb_etoiles_ho} ⭐) : {prix:.2f}€/nuit\n"

            response += f"\n💡 **Conseil :** Précisez une ville pour affiner votre recherche (ex: 'Hôtel à Paris pour {nb_personnes} personnes')."
        else:
            response = f"Désolé, aucun hôtel ne correspond à votre recherche pour {nb_personnes} personne(s)."

        dispatcher.utter_message(text=response)
        return [SlotSet("personnes", nb_personnes)]
class ActionDemanderVille(Action):
    def name(self):
        return "action_demander_ville"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):
        dispatcher.utter_message(text="Dans quelle ville souhaitez-vous rechercher un hôtel ?")
        return []


class ActionDetecterCapaciteFallback(Action):
    def name(self):
        return "action_detecter_capacite_fallback"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker, domain: dict):

        # Analyser le texte pour détecter les demandes de capacité
        message_text = tracker.latest_message.get('text', '').lower()

        mots_capacite = [
            'personne', 'personnes', 'adulte', 'adultes', 'voyageur', 'voyageurs',
            'seul', 'couple', 'groupe', 'famille', 'familial', 'familiale',
            'simple', 'double', 'triple', 'suite'
        ]

        nombres = ['1', '2', '3', '4', '5', 'une', 'un', 'deux', 'trois', 'quatre', 'cinq']

        # Vérifier si c'est une demande de capacité
        if any(mot in message_text for mot in mots_capacite) or any(nombre in message_text for nombre in nombres):
            # Rediriger vers l'action de capacité
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_rechercher_par_capacite")]
        else:
            # Ce n'est pas une demande de capacité, demander la ville normalement
            dispatcher.utter_message(
                text="Veuillez préciser la ville parmi : Paris, Lyon, Marseille, Nice, Toulouse, Bordeaux ou Lille.")
            return []