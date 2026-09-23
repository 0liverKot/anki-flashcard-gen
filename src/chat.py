from pathlib import Path
from typing import List
from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Container
from textual.widgets import Button, Label, Input, LoadingIndicator, TextArea
from concurrent.futures import Future
from src import anki
from src.source_manager import SourceManager
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
        self.source_manager = SourceManager()

        self.attempts_remaining = 3
        self.pending_cards: List[Card] = []
        self.accepted_cards: List[Card] = []
        self.proposal_container: Container | None = None
        self.proposal_counter = 0
        self.original_question: str = ""
        self.original_answer: str = ""

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

        response_future = self.model.generate_response(self.source_manager.get_current_source_json(), prompt)
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

        self.chat_container.mount(Label("I have finished generating your flashcards, just waiting for your approval now!", classes="model-text", id='finished-generating'))

        self.show_next_proposal()


    def show_next_proposal(self) -> None:
        if self.proposal_container is not None:
            self.proposal_container.remove()
            self.proposal_container = None
            
        if not self.pending_cards:
            self.display_proposals_complete()
            return

        self.proposal_counter += 1
        card = self.pending_cards[0]
        proposal_widgets = [
            Label(f"Proposal {self.proposal_counter}", classes="model-text"),
            Label(f"Question: ", classes="proposal-label"),
            TextArea(
                f"{card.front}",
                read_only=True,
                show_cursor=False,
                disabled=True,
                classes="proposal-text-area",
                id="proposal-question",
            ),
            Label(f"Answer: ", classes="proposal-label"),
            TextArea(
                f"{card.back}",
                read_only=True,
                show_cursor=False,
                disabled=True,
                classes="proposal-text-area",
                id="proposal-answer",
            ),
            Label(f"Source: {card.source}", classes="proposal-label"),
        ]
        if not self.source_manager.is_source_valid(card.source):
            invalid_source_label = Label("Issues validating source path to source file, if added the card source will not be tracked for sychronization.", classes="source-validation-label")
            proposal_widgets.append(invalid_source_label)

        self.proposal_container = Container(
            *proposal_widgets,
            classes="proposal-container",
        )
        self.chat_container.mount(self.proposal_container)

        self.display_approval_options()


    def display_proposals_complete(self) -> None:

        if len(self.accepted_cards) != 0:
            anki.add_cards(self.accepted_cards)

        self.query_one("#finished-generating").remove()

        if len(self.accepted_cards) > 1:
            complete_label = Label("Your approved cards have been added", classes="model-text")
        elif len(self.accepted_cards) == 1:
            complete_label = Label("Your approved card has been added", classes="model-text")
        else:
            complete_label = Label("No cards have been approved for addition", classes="model-text")

        
        self.chat_container.mount(complete_label, before=self.loading_response)
        
        self.user_container.border_title = None
        self.user_container.remove_children()
        
        input = Input("", id="prompt-input")
        self.user_container.mount(input)
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


    def display_approval_options(self) -> None:
        if self.query("#accept-proposal"):
            return 

        if self.query("#prompt-input"):
            self.query_one('#prompt-input').remove()

        self.user_container.border_title = "User actions are required for the given suggestion"
        approve_button = Button(label="Approve this flashcard to be added", flat=True, classes="approval-option-button", id='accept-proposal')
        edit_button = Button(label="Manual edits required", flat=True, classes="approval-option-button", id='edit-proposal')
        delete_button = Button(label="Reject this proposal", flat=True, classes="approval-option-button", id='reject-proposal')

        self.user_container.mount_all([approve_button, edit_button, delete_button])
        approve_button.focus()

    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.pending_cards:
            return

        match event.button.id:
            case "accept-proposal": 
                self.on_accept_proposal()
            case "edit-proposal": 
                self.on_edit_proposal()
            case "reject-proposal": 
                self.on_reject_proposal()
            case "accept-edit-changes":
                self.on_accept_edit_changes()
            case "discard-edit-changes":
                self.on_discard_edit_changes()


    def on_accept_proposal(self):
        self.accepted_cards.append(self.pending_cards.pop(0))
        self.show_next_proposal()


    def on_edit_proposal(self):
        question_text_area = self.query_one("#proposal-question", TextArea)
        answer_text_area = self.query_one("#proposal-answer", TextArea)

        self.original_question = question_text_area.text
        self.original_answer = answer_text_area.text

        question_text_area.read_only = False
        answer_text_area.read_only = False
        question_text_area.disabled = False
        answer_text_area.disabled = False
        question_text_area.show_cursor = True
        answer_text_area.show_cursor = True

        self.user_container.remove_children()
        accept_changes_button = Button("Accept changes", classes="approval-option-button", id="accept-edit-changes")
        discard_changes_button = Button("Discard changes", classes="approval-option-button", id="discard-edit-changes")
        self.user_container.mount_all([accept_changes_button, discard_changes_button])


    def on_reject_proposal(self):
        self.pending_cards.pop(0)
        self.show_next_proposal()


    def on_accept_edit_changes(self):
        question_text_area = self.query_one("#proposal-question", TextArea)
        answer_text_area = self.query_one("#proposal-answer", TextArea)
        
        card = self.pending_cards.pop(0)
        card.front = question_text_area.text.strip()
        card.back = answer_text_area.text.strip()

        self.accepted_cards.append(card)
        self.user_container.remove_children()
        self.show_next_proposal()


    def on_discard_edit_changes(self):
        question_text_area = self.query_one("#proposal-question", TextArea)
        answer_text_area = self.query_one("#proposal-answer", TextArea)
        
        question_text_area.text = self.original_question
        answer_text_area.text = self.original_answer

        question_text_area.disabled = True
        answer_text_area.disabled = True
        self.user_container.remove_children()
        self.display_approval_options()


if __name__ == "__main__":
    Chat().run()