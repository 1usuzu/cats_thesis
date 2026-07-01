import threading

from config import settings
from routing_templates import ROUTING_TEMPLATES


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
        self.sandbox_weights = {
            "w_latency": settings.w_latency,
            "w_queue": settings.w_queue,
            "w_compute": settings.w_compute
        }
        self.canary_active = False
        self.has_proposal = False
        self.proposed_policy = ""
        self.validation_results = {}

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

    def set_sandbox_weights(self, w_lat: float, w_queue: float, w_comp: float):
        with self.lock:
            self.sandbox_weights["w_latency"] = w_lat
            self.sandbox_weights["w_queue"] = w_queue
            self.sandbox_weights["w_compute"] = w_comp

    def get_sandbox_weights(self):
        with self.lock:
            return self.sandbox_weights.copy()

    def set_canary_active(self, active: bool):
        with self.lock:
            self.canary_active = active

    def is_canary_active(self):
        with self.lock:
            return self.canary_active

    def get_policy_proposal(self):
        with self.lock:
            return {
                "has_proposal": self.has_proposal,
                "proposed_policy": self.proposed_policy,
                "validation_results": self.validation_results.copy()
            }

    def set_policy_proposal(self, policy_text: str):
        with self.lock:
            self.has_proposal = True
            self.proposed_policy = policy_text
            self.validation_results = {"status": "PENDING"}

    def update_policy_validation(self, status: str, details: str = ""):
        with self.lock:
            self.validation_results["status"] = status
            if details:
                self.validation_results["details"] = details

    def clear_policy_proposal(self):
        with self.lock:
            self.has_proposal = False
            self.proposed_policy = ""
            self.validation_results = {}

shared_state = SharedState()
