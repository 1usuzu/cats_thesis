import threading
from routing_templates import ROUTING_TEMPLATES
from config import settings

class SharedState:
    def __init__(self):
        self.lock = threading.RLock()
        self.current_state = "STATE_NORMAL"
        self.current_template = ROUTING_TEMPLATES["STATE_NORMAL"]
        self.cost_modifiers = {"cloud": 1.0, "edge": 1.0}
        self.dynamic_weights = {
            "w_latency": settings.w_latency,
            "w_queue": settings.w_queue,
            "w_compute": settings.w_compute
        }

    def update(self, state_label):
        with self.lock:
            if state_label in ROUTING_TEMPLATES:
                self.current_state = state_label
                self.current_template = ROUTING_TEMPLATES[state_label]

    def get(self):
        with self.lock:
            return self.current_state, self.current_template.copy()

    def update_cost_modifiers(self, cloud_mod: float, edge_mod: float):
        with self.lock:
            self.cost_modifiers["cloud"] = cloud_mod
            self.cost_modifiers["edge"] = edge_mod

    def get_cost_modifiers(self):
        with self.lock:
            return self.cost_modifiers.copy()

    def update_dynamic_weights(self, w_lat: float, w_queue: float, w_comp: float):
        with self.lock:
            self.dynamic_weights["w_latency"] = w_lat
            self.dynamic_weights["w_queue"] = w_queue
            self.dynamic_weights["w_compute"] = w_comp

    def get_dynamic_weights(self):
        with self.lock:
            return self.dynamic_weights.copy()

shared_state = SharedState()
