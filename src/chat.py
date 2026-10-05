from pathlib import Path
import time
from typing import List, Tuple, cast
from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Container, Horizontal
from textual import events
from textual.widgets import Button, Label, Input, LoadingIndicator, TextArea
from textual.worker import Worker, WorkerState
from concurrent.futures import Future

from src.models.embedding_model import EmbeddingModel

from . import anki
from .db.db import DB
from .managers.source_manager import SourceManager
from .managers.duplicate_manager import DuplicateManager
from .models.flashcard_model import FlashcardModel
from .schemas import Card, NotebookData, Response_Schema
from .microsoft import onenote_service

class Chat(App):
    
    CSS_PATH = str(Path(__file__).parent / "tcss" / "chat.tcss")

    def __init__(self, token: str) -> None:
        super().__init__()

        self.token = token        

        self.db = DB()
        
        self.embedding_model = EmbeddingModel()
        self.model = FlashcardModel(self.db, self.embedding_model)

        self.unsynced_notebooks: List[NotebookData] = []
        self.source_manager = SourceManager(self.db, self.embedding_model)
        self.duplicate_manager = DuplicateManager(self.db, self.embedding_model)
        self.attempts_remaining = 3
        self.pending_cards: List[Tuple[Card, Card | None]] = []
        self.accepted_cards: List[Card] = []
        self.pending_desynced_cards: dict[int, Card] = dict()
        self.proposal_container: Container | None = None
        self.proposal_counter = 0
        self.original_question: str = ""
        self.original_answer: str = ""
        self.current_duplicate: Card | None = None
        self.showing_duplicate = False
        self.command_options = ["/sourcesync - synchronise generated cards against their sources"]
        self.syncing_cards = False
        self.syncing_card_ids: List[int] = [] 
        self.accepted_descyned_ids: List[int] = []

    def compose(self) -> ComposeResult:

        self.loading_response = LoadingIndicator(id="loading")

        self.chat_container = VerticalScroll(
            self.loading_response,
            id="model-container"
        )

        self.user_container = Vertical(
            Vertical(id="command-options"),
            Input("",id="prompt-input"),
            self.create_tooltips_container(),
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

            self.hide_command_options()
            event.input.clear()
            event.input.disabled = True
            tooltips = self.query("#tooltips-container")
            if tooltips:
                tooltips.first().remove()
            
            self.display_prompt(prompt)
            
            if prompt == "/sourcesync":
                self.run_source_sync()
                return

            self.check_onenote_synced(prompt)


    def display_model_message(self, message: str) -> None:
        self.chat_container.mount(
            Label(f"{message}", classes="model-text"),
            before=self.loading_response
        )


    def check_onenote_synced(self, prompt: str) -> None:
        self.loading_response.styles.display = 'block'
        self.display_model_message("Checking for unsynced notebooks")
        self.run_worker(
            lambda: self._run_onenote_sync(prompt),
            name="onenote-sync",
            thread=True,
        )


    def _run_onenote_sync(self, prompt: str) -> Tuple[str, List[NotebookData]]:
        return prompt, onenote_service.check_onenote_sync(self.token, self.db)


    def handle_onenote_sync_result(self, prompt: str, unsynced_notebooks: List[NotebookData]) -> None:
        self.unsynced_notebooks = unsynced_notebooks
        if len(unsynced_notebooks) == 1:
            self.display_model_message("1 unsynced notebook found")
            self.sync_notebooks(prompt)

        elif len(unsynced_notebooks) > 1:
            self.display_model_message(f"{len(unsynced_notebooks)} unsynced notebooks found")
            self.sync_notebooks(prompt)
        else:
            self.display_model_message(f"No unsynced notebooks found")
            self.send_prompt(prompt)


    def sync_notebooks(self, prompt: str):

        unsynced_notebook = self.unsynced_notebooks.pop()
        self.display_model_message(f"Syncing {unsynced_notebook.displayName}")
        self.run_worker(
            lambda: self._run_sync_notebooks(prompt, unsynced_notebook),
            name="notebook-sync",
            thread=True,
        )


    def _run_sync_notebooks(self, prompt: str, notebook: NotebookData) -> Tuple[str, None]:
        return prompt, self.source_manager.add_notebook(self.token, notebook)


    def handle_sync_notebooks_result(self, prompt: str) -> None:
        if len(self.unsynced_notebooks) == 0:
            self.display_model_message("All notebooks now synced")
            self.send_prompt(prompt)
            return

        self.sync_notebooks(prompt)


    def send_prompt(self, prompt: str) -> None:
        response_future = self.model.generate_response(prompt)
        response_future.add_done_callback(lambda future: self.handle_response(prompt, future))


    def handle_response(self, prompt: str, future: Future[Response_Schema]) -> None:
        try: 
            response = future.result()
            self.call_from_thread(self.finished_generation_message)
            similar_cards = self.duplicate_manager.check_duplicates(response.cards)
            self.call_from_thread(self.handle_response_received, response, similar_cards)
        except ValidationError: 
            if self.attempts_remaining == 0:
                self.call_from_thread(self.display_max_retries_error)
            else:    
                self.call_from_thread(self.display_validation_error, prompt)
            return

        except Exception as error:
            self.call_from_thread(self.display_general_error, error)


    def finished_generation_message(self) -> None: 
        self.chat_container.mount(Label("I have finished generating your flashcards, checking for duplicates", classes="model-text", id='finished-generating'), before=self.loading_response)


    def handle_response_received(self, response: Response_Schema, similar_cards: List[Card | None]) -> None:
        try:
            self.pending_cards = list(zip(response.cards, similar_cards))
            self.accepted_cards = []

            self.loading_response.display = 'none'

            self.show_next_proposal()
        except Exception as error:
            self.display_general_error(error)


    def show_next_proposal(self) -> None:
        for source_validation_label in self.query(".source-validation-label"):
            source_validation_label.remove()

        if self.proposal_container is not None:
            self.proposal_container.remove()
            self.proposal_container = None
        
        if self.syncing_cards:
            if not self.pending_desynced_cards:
                self.display_proposals_complete()
                return
        else: 
            if not self.pending_cards:
                self.display_proposals_complete()
                return

        self.proposal_counter += 1
        self.current_duplicate = None
        self.showing_duplicate = False

        if self.syncing_cards:
            card = self.pending_desynced_cards.get(self.syncing_card_ids[0])
            if not card:
                return
        else: 
            card, similar_card = self.pending_cards[0]
            if similar_card:
                self.current_duplicate = similar_card

        proposal_widgets = [
            Horizontal(
                Label(f"Proposal {self.proposal_counter}"),
                *(
                    [Label(
                        "Potential duplicate detected, press i to inspect",
                        classes="duplicate-inspection-label",
                        id="duplicate-inspection",
                    )]
                    if self.current_duplicate
                    else []
                ),
                classes="proposal-header",
            ),
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
            Label(f"Source: {card.source}", classes="proposal-label", id="proposal-source"),
        ]
        
        # cards from synchronisation will have a valid source associated with them
        if not self.syncing_cards and not self.source_manager.is_source_valid(card.source):
            invalid_source_label = Label("Issues validating source path to source file, if added the card source will not be tracked for sychronization.", classes="source-validation-label")
            proposal_widgets.append(invalid_source_label)

        self.proposal_container = Container(
            *proposal_widgets,
            classes="proposal-container",
        )
        self.chat_container.mount(self.proposal_container)

        self.display_approval_options()

    def on_key(self, event: events.Key) -> None:
        if event.key != "i" or self.current_duplicate is None:
            return

        focused_widget = self.focused
        if isinstance(focused_widget, TextArea) and not focused_widget.disabled:
            return

        self.toggle_duplicate_inspection()
        event.stop()


    def toggle_duplicate_inspection(self) -> None:
        if self.current_duplicate is None:
            return

        question_text_area = self.query_one("#proposal-question", TextArea)
        answer_text_area = self.query_one("#proposal-answer", TextArea)
        source_label = self.query_one("#proposal-source", Label)
        inspection_label = self.query_one("#duplicate-inspection", Label)

        self.showing_duplicate = not self.showing_duplicate
        if self.showing_duplicate:
            question_text_area.text = self.current_duplicate.front
            answer_text_area.text = self.current_duplicate.back
            source_label.display = False
            inspection_label.update("Press i to go back to the proposal")
        else:
            card, _ = self.pending_cards[0]
            question_text_area.text = card.front
            answer_text_area.text = card.back
            source_label.update(f"Source: {card.source}")
            source_label.display = True
            inspection_label.update("Potential duplicate detected, press i to inspect")


    def display_proposals_complete(self) -> None:

        if len(self.accepted_cards) != 0:

            if self.syncing_cards:
                anki.update_cards(self.accepted_descyned_ids, self.accepted_cards)
                self.source_manager.update_sources(self.accepted_descyned_ids, self.accepted_cards)
            else: 
                card_ids = anki.add_cards(self.accepted_cards)
                self.source_manager.add_card_sources(self.accepted_cards, card_ids)
                self.duplicate_manager.add_cards(self.accepted_cards)

        self.query_one("#finished-generating").remove()

        if len(self.accepted_cards) > 1:
            complete_label = Label("Your approved cards have been added", classes="model-text")
        elif len(self.accepted_cards) == 1:
            complete_label = Label("Your approved card has been added", classes="model-text")
        else:
            complete_label = Label("No cards have been approved for addition", classes="model-text")

        
        self.chat_container.mount(complete_label, before=self.loading_response)
        
        self.user_container.border_title = None
        self.user_container.query(".approval-option-button").remove()

        input = Input("", id="prompt-input")
        self.user_container.mount_all([
            input,
            self.create_tooltips_container()
        ])
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
        
        self.ensure_tooltips_container()
        input = self.query_one('#prompt-input')
        input.disabled = False
        input.focus()


    def display_general_error(self, error: BaseException) -> None:
        self.loading_response.styles.display = 'none'
        error_label = Label(
            f"Something went wrong: {type(error).__name__}: {error}",
            classes="error",
        )
        self.chat_container.mount(error_label, before=self.loading_response)
        self.attempts_remaining = 3


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
        if not self.pending_cards and not self.pending_desynced_cards:
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
        if self.syncing_cards:
            card_id = self.syncing_card_ids.pop(0)    
            card = self.pending_desynced_cards.pop(card_id)
            self.accepted_descyned_ids.append(card_id)
        else:
            card, _ = self.pending_cards.pop(0)

        self.accepted_cards.append(card)
        self.show_next_proposal()


    def on_edit_proposal(self):
        if self.showing_duplicate:
            self.toggle_duplicate_inspection()

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
        if self.syncing_cards:
            self.pending_desynced_cards.pop(self.syncing_card_ids.pop(0))
        else:
            self.pending_cards.pop(0)
        self.show_next_proposal()


    def on_accept_edit_changes(self):
        question_text_area = self.query_one("#proposal-question", TextArea)
        answer_text_area = self.query_one("#proposal-answer", TextArea)
        
        if self.syncing_cards:
            card_id = self.syncing_card_ids.pop(0)
            card = self.pending_desynced_cards.pop(card_id)
            self.accepted_descyned_ids.append(card_id)
        else:
            card, _ = self.pending_cards.pop(0)

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


    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "prompt-input":
            return

        command_options = self.query_one("#command-options", Vertical)
        command_options.remove_children()

        if not event.value.startswith("/"):
            command_options.display = False
            return

        matching_commands = [
            command for command in self.command_options
            if command.lower().startswith(event.value.lower())
        ]
        if not matching_commands:
            command_options.display = False
            return

        command_options.mount_all(
            Label(command, classes="command-option")
            for command in matching_commands
        )
        command_options.display = True


    def hide_command_options(self) -> None:
        command_options = self.query("#command-options")
        if command_options:
            command_options.first().display = False


    def create_tooltips_container(self) -> Horizontal:
        return Horizontal(
                    Label("● Ctrl-q Exit", classes="shortcut-tooltip"),
                    Label("● / Commands", classes="shortcut-tooltip"),
                    id="tooltips-container"
                    )

    def ensure_tooltips_container(self) -> None:
        if not self.query("#tooltips-container"):
            self.user_container.mount(self.create_tooltips_container())


    def run_source_sync(self) -> None:
        self.chat_container.mount(
            Label("Checking synchronisation between generated cards and their sources", classes="model-text"),
            before=self.loading_response
        )
        self.loading_response.styles.display = 'block'
        self.run_worker(self._run_source_sync, name="source-sync", thread=True)
        return
    
    def _run_source_sync(self) -> List[int]:
        return self.source_manager.synchronise()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        worker = event.worker
        if worker.name == "onenote-sync":
            self.one_note_worker_changed(event, worker)

        if worker.name == "source-sync":
            self.source_sync_worker_changed(event, worker)
        
        if worker.name == "notebook-sync":
            self.notebook_sync_worker_changed(event, worker)


    def notebook_sync_worker_changed(self, event: Worker.StateChanged, worker: Worker) -> None:
        
        if event.state == WorkerState.SUCCESS:
            result = cast(Worker[Tuple[str, None]], worker).result
            
            assert result is not None
            prompt, _ = result
            self.handle_sync_notebooks_result(prompt)
        
        elif event.state == WorkerState.ERROR:
            error = worker.error
            if error is not None:
                self.display_general_error(error)
            
            self.ensure_tooltips_container()
            input = self.query_one("#prompt-input")
            input.disabled = False
            input.focus()
        return


    def source_sync_worker_changed(self, event: Worker.StateChanged, worker: Worker) -> None:
        
        if event.state != WorkerState.SUCCESS:
            return
        
        time.sleep(1)

        worker = cast(Worker[List[int]], event.worker)
        desynced = worker.result
        assert desynced is not None

        if not desynced or len(desynced) == 0:
            self.chat_container.mount(
                Label("0 desynced cards found", classes="model-text"),
                before=self.loading_response
            )
            self.loading_response.styles.display = "none"
            self.ensure_tooltips_container()
            input= self.query_one("#prompt-input")
            input.disabled = False
            input.focus()
        else: 
            self.chat_container.mount(
                Label(f"{len(desynced)} desynced cards found, generating revised versions", classes="model-text"),
                before=self.loading_response
            )
            self.handle_desynced_cards_found(desynced)


    def one_note_worker_changed(self, event: Worker.StateChanged, worker: Worker) -> None:
        
        if event.state == WorkerState.SUCCESS:
            result = cast(Worker[Tuple[str, List[NotebookData]]], worker).result
            
            assert result is not None
            prompt, unsynced_notebooks = result
            self.handle_onenote_sync_result(prompt, unsynced_notebooks)
        
        elif event.state == WorkerState.ERROR:
                error = worker.error
                if error is not None:
                    self.display_general_error(error)
                
                self.ensure_tooltips_container()
                input = self.query_one("#prompt-input")
                input.disabled = False
                input.focus()
        return

    def handle_desynced_cards_found(self, desynced_ids: List[int]) -> None:
        
        self.syncing_cards = True
        self.syncing_card_ids = desynced_ids

        source_paths = self.source_manager.get_source_paths(desynced_ids)
        new_sources = self.source_manager.get_sources(source_paths)
        
        for id, path in source_paths.items(): 

            response_future = self.model.generate_single_card(id, path, new_sources[id])
            response_future.add_done_callback(lambda future, card_id=id: self.handle_single_card_generated(card_id, future))


    def handle_single_card_generated(self, id: int, future: Future[Card]) -> None:
        response = future.result()
        self.call_from_thread(self.handle_single_card_received, id, response) 


    def handle_single_card_received(self, id: int, response: Card) -> None:
        self.pending_desynced_cards[id] = response
        
        if len(self.pending_desynced_cards) == len(self.syncing_card_ids):
            self.loading_response.styles.display = 'none'
            self.chat_container.mount(Label("I have finished revising your desynced flashcards, just waiting for your approval now!", classes="model-text", id='finished-generating'))
            self.show_next_proposal()