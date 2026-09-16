import ollama
from concurrent.futures import ThreadPoolExecutor, Future

class Model: 

    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=1)


    def generate_response(self, prompt: str) -> Future[str]:
        return self.executor.submit(self._generate_response, prompt)

    def _generate_response(self, prompt: str) -> str:
        response = ollama.chat(
            model="qwen3:8b",
            messages=[{"role": "user", "content": prompt}],
            think=False
        )

        return response["message"]["content"]