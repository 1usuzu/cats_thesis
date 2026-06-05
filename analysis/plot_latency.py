import matplotlib.pyplot as plt
import pandas as pd
import os
import glob

def plot_latency_comparison():
    # Read Locust CSV results
    results_dir = "../results"
    files = glob.glob(os.path.join(results_dir, "*_stats.csv"))
    
    if not files:
        print("No locust results found.")
        return

    data = {}
    for f in files:
        scenario = os.path.basename(f).replace("locust_", "").replace("_stats.csv", "")
        df = pd.read_csv(f)
        # Average response time for POST /v1/chat
        avg_rt = df[df["Name"] == "/v1/chat"]["Average Response Time"].values
        if len(avg_rt) > 0:
            data[scenario] = avg_rt[0]

    if not data:
        print("No valid chat data found.")
        return

    scenarios = list(data.keys())
    latencies = list(data.values())

    plt.figure(figsize=(10, 6))
    bars = plt.bar(scenarios, latencies, color='skyblue')
    plt.title("Average Response Time by Scenario")
    plt.ylabel("Response Time (ms)")
    plt.xticks(rotation=45)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 10, f'{yval:.0f}', ha='center', va='bottom')
        
    plt.tight_layout()
    os.makedirs("plots", exist_ok=True)
    plt.savefig("plots/latency_comparison.png")
    print("Saved plots/latency_comparison.png")

if __name__ == "__main__":
    # Assuming run from analysis/ directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    plot_latency_comparison()
