import ollama
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future

try:
    from .schemas import Response_Schema
except ImportError:
    from schemas import Response_Schema

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
        - The tag must describe the card using one of the following options: Definition, Explanation, Advantages, Disadvantages, Evaluation or Other
        - sources must contain the full path 

        Return JSON in this exact shape:
        {{
        "cards": [
            {{
            "front": "Question",
            "back": "Answer",
            "tags": "topic",
            "source": "source path"
            }}
        ]
        }}                
        
        """
