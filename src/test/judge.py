import ollama 
try:
    from ..schemas import Card, Judge_Schema
except ImportError:
    from schemas import Card, Judge_Schema

class Judge:

    def judge_output(self, source: str, flashcard: Card):

        system_prompt = self.generate_system_prompt(source, flashcard)     

        response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": system_prompt},
            ],
            think=True,
            format=Judge_Schema.model_json_schema()
        )

        return Judge_Schema.model_validate_json(response["message"]["content"])


    def generate_system_prompt(self, source: str, flashcard: Card):

        return f"""
        You are an impartial LLM judge evaluating a generated flashcard against the provided source material.

        Evaluate the flashcards quality using only the source material and the flashcard itself. Do not use outside knowledge to fill gaps or validate claims. 

        Use the source of the flashcard to help locate the text supporting this flashcard, if you cannot find it using this look through the entire source text. This does not impact groundedness however you should take note of this in your overall explanation.

        Score the following dimensions:

        1. Groundedness (0-2)
        - 2: The question and answer are fully supported by the source material and do not introduce unsupported claims.
        - 1: The flashcard is partly supported, but contains a minor unsupported detail, weak inference, or omission.
        - 0: The flashcard is substantially unsupported, contradicts the source, or relies on information absent from it.

        2. Atomicity (0-1)
        - 1: The flashcard tests one distinct, focused idea or fact that can be recalled and evaluated independently.
        - 0: The flashcard combines multiple unrelated facts, asks several questions at once, or is too broad to answer as a single unit.

        3. Usefulness (0-2)
        Assess pedagogical value: whether the flashcard is worth studying and supports meaningful recall or understanding.
        - 2: The flashcard tests important, relevant knowledge and would clearly help the learner understand or remember the material.
        - 1: The flashcard has some learning value but is overly trivial, overly specific, redundant, or only moderately relevant.
        - 0: The flashcard is not useful for learning, tests irrelevant details, or provides little meaningful practice.

        4. Clarity (0-2)
        - 2: The question and answer are clear, precise, unambiguous, and appropriately concise.
        - 1: The intended meaning is mostly clear, but the wording is vague, awkward, overly verbose, or mildly ambiguous.
        - 0: The flashcard is confusing, malformed, unanswerable, or ambiguous enough that multiple answers could reasonably fit.

        5. Overall score (0-2)
        Give a holistic rating of the flashcard, considering all four dimensions and the importance of any weaknesses.
        - 2: High-quality flashcard that is well-grounded, focused, useful, and clear.
        - 1: Usable but has notable weaknesses in one or more dimensions.
        - 0: Poor-quality flashcard that should be rejected or substantially rewritten.

        Return only valid JSON in this exact format:

        {{
        "groundedness": <integer from 0 to 2>,
        "atomicity": <integer from 0 to 1>,
        "usefulness": <integer from 0 to 2>,
        "clarity": <integer from 0 to 2>,
        "overall": <integer from 0 to 2>,
        "explanation": "<one or two concise sentences explaining the scores>"
        }}

        The explanation should briefly identify the most important strengths or weaknesses. It may mention unsupported claims, multiple facts, low pedagogical value, ambiguity, verbosity, or other issues affecting the scores. Do not quote large portions of the source or flashcard.

        Source text:
        {source}

        Generated flashcard:
        {flashcard.model_dump_json()}
        """