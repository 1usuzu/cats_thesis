import threading
from routing_templates import ROUTING_TEMPLATES

class SharedState:
    def __init__(self):
        self.lock = threading.RLock()
        self.current_state = "STATE_NORMAL"
        self.current_template = ROUTING_TEMPLATES["STATE_NORMAL"]

    def update(self, state_label):
        with self.lock:
            if state_label in ROUTING_TEMPLATES:
                self.current_state = state_label
                self.current_template = ROUTING_TEMPLATES[state_label]

    def get(self):
        with self.lock:
            return self.current_state, self.current_template.copy()

shared_state = SharedState()
