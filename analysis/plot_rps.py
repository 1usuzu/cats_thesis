import matplotlib.pyplot as plt
import pandas as pd
import os
import glob

def plot_rps():
    results_dir = "../results"
    files = glob.glob(os.path.join(results_dir, "*_stats_history.csv"))
    
    if not files:
        return

    plt.figure(figsize=(12, 6))
    
    for f in files:
        scenario = os.path.basename(f).replace("locust_", "").replace("_stats_history.csv", "")
        df = pd.read_csv(f)
        
        # Filter for the main POST request
        df_chat = df[df["Name"] == "/v1/chat"]
        if not df_chat.empty:
            plt.plot(df_chat["Timestamp"] - df_chat["Timestamp"].min(), df_chat["Requests/s"], label=scenario)

    plt.title("Requests Per Second (Throughput) Over Time")
    plt.xlabel("Time (s)")
    plt.ylabel("RPS")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    os.makedirs("plots", exist_ok=True)
    plt.savefig("plots/rps_over_time.png")
    print("Saved plots/rps_over_time.png")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    plot_rps()
