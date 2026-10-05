from typing import List
import ollama
from concurrent.futures import ThreadPoolExecutor, Future

from src.db.db import DB
from src.managers.retrieval_manager import RetrievalManager
from src.models.embedding_model import EmbeddingModel
from .. import anki
from ..schemas import Card, Chunk_Schema, Response_Schema, Single_Card_Response_Schema

class FlashcardModel: 

    def __init__(self, db: DB, embedding_model: EmbeddingModel) -> None:
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.retrieval_manager = RetrievalManager(db, embedding_model)

    def generate_response(self, prompt: str) -> Future[Response_Schema]:
        return self.executor.submit(self._generate_response, prompt)

    def _generate_response(self, user_prompt: str = "") -> Response_Schema:
        
        if user_prompt == "":
            user_prompt = "make flashcards using the source and instructions in the system prompt"

        chunks = self.retrieval_manager.get_chunks(user_prompt)
        system_prompt = self.generate_system_prompt(chunks)
        
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
    

    def generate_system_prompt(self, chunks):
        
        context = self.build_context(chunks)
        
        return f"""
        You generate high-quality Anki flashcards from source material. 
        
        Source:
        {context}

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
    
    def build_context(self, chunks: List[Chunk_Schema]):
        context = ""
        for chunk in chunks:
            context += f"Source: {chunk.source_path} \n Content: {chunk.content}\n\n"
        return context

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