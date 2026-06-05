import matplotlib.pyplot as plt
import pandas as pd
import os
import glob
import seaborn as sns

def plot_ttft_distribution():
    results_dir = "../results"
    files = glob.glob(os.path.join(results_dir, "*_stats.csv"))
    
    if not files:
        return

    data = []
    for f in files:
        scenario = os.path.basename(f).replace("locust_", "").replace("_stats.csv", "")
        df = pd.read_csv(f)
        
        # We fired custom events for routing with TTFT as response_time
        # Since Locust's stats.csv only gives aggregate data (Min, Max, Avg, Median), 
        # we'll plot the Average TTFT for Cloud and Edge separately.
        cloud_ttft = df[df["Name"] == "Routed to cloud"]["Average Response Time"].values
        edge_ttft = df[df["Name"] == "Routed to edge"]["Average Response Time"].values
        
        c_ttft = cloud_ttft[0] if len(cloud_ttft) > 0 and not pd.isna(cloud_ttft[0]) else 0
        e_ttft = edge_ttft[0] if len(edge_ttft) > 0 and not pd.isna(edge_ttft[0]) else 0
        
        data.append({"Scenario": scenario, "Cloud TTFT (ms)": c_ttft, "Edge TTFT (ms)": e_ttft})

    if not data:
        return

    df_plot = pd.DataFrame(data).set_index("Scenario")
    
    # Filter out empty rows if neither site was used
    df_plot = df_plot[(df_plot["Cloud TTFT (ms)"] > 0) | (df_plot["Edge TTFT (ms)"] > 0)]
    
    ax = df_plot.plot(kind='bar', figsize=(10, 6), color=['#1f77b4', '#ff7f0e'])
    plt.title("Average Time To First Token (TTFT) by Routing Decision")
    plt.ylabel("TTFT (ms)")
    plt.xticks(rotation=45)
    plt.legend(title="Routed To")
    
    for container in ax.containers:
        ax.bar_label(container, fmt='%.0f', padding=3)

    plt.tight_layout()
    os.makedirs("plots", exist_ok=True)
    plt.savefig("plots/ttft_comparison.png")
    print("Saved plots/ttft_comparison.png")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    plot_ttft_distribution()
