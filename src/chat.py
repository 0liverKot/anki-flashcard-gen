from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Label, Input, LoadingIndicator
from flashcard_model import FlashcardModel
from concurrent.futures import Future

from schemas import Response_Schema

class Chat(App):
    CSS_PATH = "tcss/chat.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.model = FlashcardModel()
        self.attempts_remaining = 3


    def compose(self) -> ComposeResult:

        self.loading_response = LoadingIndicator(id="loading")

        self.chat_container = VerticalScroll(
            self.loading_response,
            id="model-container"
        )

        self.user_container = Vertical(
            Input("",id="prompt-input"),
            id="user-container"
        )

        yield self.chat_container
        yield self.user_container


    def on_mount(self) -> None:
        self.chat_container.border_title = "Ankify"
        self.loading_response.styles.display = 'none'
        
        input = self.query_one('#prompt-input')
        input.focus()


    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'prompt-input':
            
            prompt = event.value.strip()
            if not prompt:
                return

            event.input.clear()
            event.input.disabled = True

            self.display_prompt(prompt)
            self.send_prompt(prompt)


    def send_prompt(self, prompt: str) -> None:
            self.loading_response.styles.display = 'block'
            response_future = self.model.generate_response(prompt)
            response_future.add_done_callback(lambda future: self.handle_response(prompt, future))


    def handle_response(self, prompt: str, future: Future[Response_Schema]) -> None:
        try: 
            response = future.result()
        except ValidationError: 
            if self.attempts_remaining == 0:
                self.call_from_thread(self.display_max_retries_error)
            else:    
                self.call_from_thread(self.display_validation_error, prompt)

        # UI update must be done on Textual UI's thread
        # handle_response is running on a background thread
        self.call_from_thread(self.display_response, response) 


    def display_response(self, response: Response_Schema) -> None:

        # returning temporary states to orgininal
        self.loading_response.display = 'none'
        input = self.query_one('#prompt-input')
        input.disabled = False
        input.focus()

        response_text = response.model_dump_json(indent=2)        

        # diaplaying reesponse
        response_label = Label(response_text, classes="response")
        self.chat_container.mount(response_label, before=self.loading_response)


    def display_prompt(self, prompt: str) -> None:
        prompt_label = Label(f'> {prompt}', classes="prompt")
        self.chat_container.mount(prompt_label, before=self.loading_response)
        self.attempts_remaining = 3


    def display_validation_error(self, prompt: str) -> None:
        self.loading_response.display = 'none'

        if self.attempts_remaining == 1:
            error_text = "Something went wrong validating flashcard outputs, 1 attempt remaining"
        else: 
            error_text = f"Something went wrong validating flashcard outputs, {self.attempts_remaining} attempts remaining"

        error_label = Label(error_text, classes="error")
        self.chat_container.mount(error_label, before=self.loading_response)
        self.attempts_remaining -= 1

        self.send_prompt(prompt)

    
    def display_max_retries_error(self) -> None:
        self.loading_response.display = 'none'
        error_label = Label("Reached the maximum number of attempts.", classes="error")
        self.chat_container.mount(error_label, before=self.loading_response)
        self.attempts_remaining = 3
        
        input = self.query_one('#prompt-input')
        input.disabled = False
        input.focus()


if __name__ == "__main__":
    Chat().run()