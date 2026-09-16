import ollama
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from md_parser import md_to_json
from schemas import Response_Model

class Model: 

    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.PATH = Path(__file__).parent / "notes" / "waves_and_particle_nature_of_light.md"


    def generate_response(self, prompt: str) -> Future[Response_Model]:
        return self.executor.submit(self._generate_response, prompt)

    def _generate_response(self, user_prompt: str) -> Response_Model:
        
        system_prompt = self.generate_system_prompt()
        
        response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
                ],
            think=False,
            format="json"
        )

        return Response_Model.model_validate_json(response["message"]["content"])
    

    def generate_system_prompt(self):
        file_json = md_to_json(self.PATH)

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
            "source": "source"
            }}
        ]
        }}                
        
        """

