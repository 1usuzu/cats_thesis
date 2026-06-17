import json
import os
import random

PROMPTS = [
    "Write a short essay on the history of Rome.",
    "Can you explain the theory of relativity?",
    "Summarize the plot of Hamlet.",
    "Give me 5 Python tips.",
    "Translate 'Hello world' into French, Spanish, and German.",
    "Write a poem about a rainy day.",
    "What are the benefits of machine learning?",
    "Explain how a combustion engine works.",
    "Write a short story about a time traveler.",
    "What is the capital of Australia?"
]

TAGS = ["default", "fast_ok", "high_quality"]

def generate_prompts(num=500):
    data = []
    for _ in range(num):
        prompt = random.choice(PROMPTS) + f" (Variation {random.randint(1, 1000)})"
        tag = random.choices(TAGS, weights=[0.7, 0.15, 0.15])[0]
        data.append({"prompt": prompt, "request_tag": tag})
    return data

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    out_file = "data/prompts.json"
    with open(out_file, "w") as f:
        json.dump(generate_prompts(500), f, indent=2)
    print(f"Generated 500 prompts to {out_file}")
