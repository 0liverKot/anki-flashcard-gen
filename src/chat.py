from pathlib import Path
from typing import List
from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Container
from textual.widgets import Button, Label, Input, LoadingIndicator
from concurrent.futures import Future

try:
    from .flashcard_model import FlashcardModel
    from .schemas import Card, Response_Schema
except ImportError:
    from flashcard_model import FlashcardModel
    from schemas import Card, Response_Schema

class Chat(App):
    CSS_PATH = str(Path(__file__).parent / "tcss" / "chat.tcss")

    def __init__(self) -> None:
        super().__init__()
        self.model = FlashcardModel()
        self.attempts_remaining = 3
        self.pending_cards: List[Card] = []
        self.accepted_cards: List[Card] = []
        self.proposal_container: Container | None = None


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
            return

        # UI update must be done on Textual UI's thread
        # handle_response is running on a background thread
        self.call_from_thread(self.handle_response_received, response) 


    def handle_response_received(self, response: Response_Schema) -> None:

        self.loading_response.display = 'none'

        self.pending_cards = response.cards
        self.accepted_cards = []
        self.show_next_proposal()


    def show_next_proposal(self) -> None:
        if self.proposal_container is not None:
            self.proposal_container.remove()
            self.proposal_container = None
            
        if not self.pending_cards:
            self.display_proposals_complete()
            return

        card = self.pending_cards[0]
        self.proposal_container = Container(
            Label(f"Question:\n{card.front}"),
            Label(f"Answer:\n{card.back}"),
            Button("Accept", id="accept-proposal", variant="success"),
            classes="proposal-container"
        )
        self.chat_container.mount(self.proposal_container)


    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "accept-proposal" or not self.pending_cards:
            return

        self.accepted_cards.append(self.pending_cards.pop(0))
        self.show_next_proposal()


    def display_proposals_complete(self) -> None:
        if len(self.accepted_cards) > 1:
            complete_label = Label("Your cards have been added")
        else:
            complete_label = Label("Your card has been added")
            

        self.chat_container.mount(complete_label, before=self.loading_response)
        input = self.query_one("#prompt-input")
        input.disabled = False
        input.focus()


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