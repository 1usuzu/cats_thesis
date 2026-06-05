import asyncio
import httpx
import json
import os
from evaluate import load # from huggingface evaluate

async def evaluate_rouge():
    rouge = load('rouge')
    
    prompts = [
        "Explain the theory of relativity.",
        "What are the benefits of Docker?",
        "Write a python script to parse JSON."
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for p in prompts:
            print(f"Testing quality for prompt: {p[:30]}...")
            try:
                res = await client.post("http://localhost:8000/v1/quality-sample", json={
                    "prompt": p
                }, headers={"X-API-Key": os.getenv("CATS_API_KEY", "")})
                res.raise_for_status()
                data = res.json()
                
                cloud_resp = data.get("cloud_response", "")
                edge_resp = data.get("edge_response", "")
                
                results.append((cloud_resp, edge_resp))
            except Exception as e:
                print(f"Failed to query quality endpoint: {e}")

    # Compute ROUGE
    cloud_texts = [r[0] for r in results if r[0] and r[1]]
    edge_texts = [r[1] for r in results if r[0] and r[1]]
    
    if cloud_texts and edge_texts:
        rouge_scores = rouge.compute(predictions=edge_texts, references=cloud_texts)
        print("\nROUGE Scores (Edge vs Cloud Reference):")
        print(json.dumps(rouge_scores, indent=2))
        
        # Save results
        os.makedirs("results", exist_ok=True)
        with open("results/rouge_eval.json", "w") as f:
            json.dump(rouge_scores, f, indent=2)
    else:
        print("No valid responses to evaluate.")

if __name__ == "__main__":
    asyncio.run(evaluate_rouge())
