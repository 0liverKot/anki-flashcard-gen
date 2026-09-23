import json 
import urllib.request
from typing import List
from src.schemas import Card

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
    for card in cards:
        flashcard = {
            "deckName": "Test",
            "modelName": "Basic",
            "fields": {
                "Front": card.front,
                "Back": card.back
            },
            "tags": card.tags
        }
        invoke(action="addNote", note=flashcard)
