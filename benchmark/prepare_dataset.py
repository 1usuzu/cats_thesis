import json
import random
import os

PROMPTS = [
    "Explain the concept of quantum computing in simple terms.",
    "Write a short python script to parse a CSV file.",
    "What are the main differences between React and Vue?",
    "Summarize the plot of Inception.",
    "Give me 5 tips for better time management.",
    "How does a neural network work?",
    "Write a SQL query to find the second highest salary.",
    "What is the capital of Australia?",
    "Translate 'Hello, how are you?' to French.",
    "Explain the theory of relativity.",
    "Write a haiku about programming.",
    "What are the benefits of Docker?",
    "Write a short email apologizing for a delay.",
    "How do I reverse a string in JavaScript?",
    "What is the significance of the Turing test?",
    "Explain the difference between TCP and UDP.",
    "Write a bash script to backup a directory.",
    "What are the core principles of Agile methodology?",
    "Describe the lifecycle of a butterfly.",
    "How does blockchain technology work?"
]

def generate_dataset(num_samples: int = 1000):
    dataset = []
    for _ in range(num_samples):
        # 70% default, 20% fast_ok, 10% high_quality
        r = random.random()
        if r < 0.7:
            tag = "default"
        elif r < 0.9:
            tag = "fast_ok"
        else:
            tag = "high_quality"
            
        dataset.append({
            "prompt": random.choice(PROMPTS),
            "request_tag": tag
        })
        
    os.makedirs("data", exist_ok=True)
    with open("data/prompts.json", "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {num_samples} prompts in data/prompts.json")

if __name__ == "__main__":
    generate_dataset()
