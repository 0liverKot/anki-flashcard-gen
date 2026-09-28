import json 
import urllib.request
from typing import List

try:
    from src.schemas import Card
except ModuleNotFoundError:
    from schemas import Card

import logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']


def add_cards(cards: List[Card]):
    card_ids = list()
    for card in cards:
        flashcard = {
            "deckName": "Test",
            "modelName": "Basic",
            "fields": {
                "Front": card.front,
                "Back": card.back
            },
        }
        card_id = invoke(action="addNote", note=flashcard)
        card_ids.append(card_id)
    return card_ids


def get_question(id: int):
    question_result = invoke(action="notesInfo", notes=[id])
    
    return question_result[0]['fields']['Front']['value']


def update_cards(ids: List[int], cards: List[Card]) -> None:
    
    for note_id, card in zip(ids, cards):
        note = {
            "id": note_id,
            "fields": {
                "Front": card.front,
                "Back": card.back,
            },
        }

        logger.info("Updating note %s with %s", note_id, note)
        result = invoke("updateNote", note=note)
        logger.info("AnkiConnect response for note %s: %r", note_id, result)

        updated = invoke("notesInfo", notes=[note_id])[0]
        logger.info(
            "Updated fields: Front=%r Back=%r",
            updated["fields"]["Front"]["value"],
            updated["fields"]["Back"]["value"],
        )
