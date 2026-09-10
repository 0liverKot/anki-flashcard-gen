from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Input, LoadingIndicator
from model import Model
from concurrent.futures import Future

class Chat(App):
    CSS_PATH = "tcss/chat.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.model = Model()

    def compose(self) -> ComposeResult:

        self.loading_response = LoadingIndicator(id="loading")

        self.model_container = Container(
            self.loading_response,
            id="model-container"
        )

        self.user_container = Vertical(
            Input("",id="prompt-input"),
            id="user-container"
        )

        yield self.model_container
        yield self.user_container

    def on_mount(self) -> None:
        self.model_container.border_title = "Ankify"
        self.loading_response.styles.display = 'none'

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'prompt-input':
            
            prompt = event.value
            event.input.clear()
            event.input.disabled = True

            self.loading_response.styles.display = 'block'
            
            response_future = self.model.generate_response(prompt)
            response_future.add_done_callback(self.handle_response)


    def handle_response(self, future: Future[str]) -> None:
        response = future.result()

        # UI update must be done on Textual UI's thread
        # handle_response is running on a background thread
        self.call_from_thread(self.display_response, response) 


    def display_response(self, response: str) -> None:

        # returning temporary states to orgininal
        self.loading_response.display = 'none'
        input = self.query_one('#prompt-input')
        input.disabled = False
        input.focus()
        

        # diaplaying reesponse
        response_label = Label(response, classes="response")
        self.model_container.mount(response_label, before=self.loading_response)

if __name__ == "__main__":
    Chat().run()