from pathlib import Path
from ..flashcard_model import FlashcardModel
from .judge import Judge
from ..schemas import Card, Judge_Schema

from ..md_parser import md_to_json

def format_judge_response(response: Judge_Schema):
    return f"""
Results:

Groudnedness: {response.groundedness}
Atomicity: {response.atomicity}
Usefulness: {response.usefulness}
Clarity: {response.clarity}

Overall: {response.overall}
Explanation: {response.explanation}

    """

def format_card(card: Card):
    return f"""
Front:

{card.front}

Back:

{card.back}

Source: 

{card.source}
    """

def main():
    PATH = Path(__file__).parents[1] / "notes" / "waves_and_particle_nature_of_light.md"

    flashcard_model = FlashcardModel()
    judge = Judge()

    file_json = md_to_json(PATH)
    flashcards = flashcard_model._generate_response().cards
    
    num_cards = len(flashcards)
    print(f"\n{num_cards} flashcards generated, starting evaluation")

    count = 1
    for card in flashcards:

        print(f"Judging card {count}:")
        print(format_card(card))

        judge_response = judge.judge_output(file_json, card)
        print(judge_response)
        print(format_judge_response(judge_response))
        
        count += 1


if __name__ == "__main__":
    main()
