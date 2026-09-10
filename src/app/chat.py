from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Input

import model

class Chat(App):
    CSS_PATH = "tcss/chat.tcss"

    def compose(self) -> ComposeResult:
        self.model_container = Container(
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


    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'prompt-input':
            response = model.send_prompt(event.value)

            response_label = Label(f"{response}")
            self.model_container.mount(response_label)

if __name__ == "__main__":
    Chat().run()