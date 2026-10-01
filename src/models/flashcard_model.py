from typing import List
import ollama
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future

from pydantic import ValidationError

try:
    from src import anki
    from src.schemas import Card
except ModuleNotFoundError:
    from schemas import Card
    import anki
try:
    from ..schemas import Response_Schema, Single_Card_Response_Schema
except ImportError:
    from schemas import Response_Schema, Single_Card_Response_Schema

class FlashcardModel: 

    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.PATH = Path(__file__).parent / "notes" / "waves_and_particle_nature_of_light.md"

    def generate_response(self, file_json: str, prompt: str) -> Future[Response_Schema]:
        return self.executor.submit(self._generate_response, file_json, prompt)

    def _generate_response(self, file_json: str, user_prompt: str = "") -> Response_Schema:
        
        if user_prompt == "":
            user_prompt = "make flashcards using the source and instructions in the system prompt"

        system_prompt = self.generate_system_prompt(file_json)
        
        response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
                ],
            think=False,
            format=Response_Schema.model_json_schema()
        )

        return Response_Schema.model_validate_json(response["message"]["content"])
    

    def generate_system_prompt(self, file_json):

        return f"""
        You generate high-quality Anki flashcards from source material.
        
        Source:
        {file_json}

        Rules:
        - Create atomic cards: one fact or concept per card.
        - Prefer clear questions over vague prompts.
        - Keep answers concise but complete.
        - Do not invent information absent from the source.
        - The source for the flashcard must be the exact same as labelled in the source json provided

        Return JSON in this exact shape:
        {{
        "cards": [
            {{
            "front": "Question",
            "back": "Answer",
            "source": "source path"
            }}
        ]
        }}                
        
        """

    def generate_single_card(self, id: int, source_path: str, source: str) -> Future[Card]:
        return self.executor.submit(self._generate_single_card, id, source_path, source)

    def _generate_single_card(self, id: int, source_path: str, source: str) -> Card:

        
        question = anki.get_question(id)

        system_prompt = f"""

            You find answers for a given question and source intended to be used for a flashcard

            Source:
            {source}

            Question:
            {question}

            Rules: 
            - Keep answers concise but complete.
            - Do not invent information absent from the source.

            reutrn JSON in thsi exact shape:

            {{
            answer: "Answer"
            }}

        """

        response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "return a suitable answer for the given question backed by the source"}
                ],
            think=False,
            format=Single_Card_Response_Schema.model_json_schema()
        )

        validated_response = Single_Card_Response_Schema.model_validate_json(response["message"]["content"])

        return Card(
            front=question,
            back=validated_response.answer,
            source=source_path
        )