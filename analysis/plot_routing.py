import matplotlib.pyplot as plt
import pandas as pd
import os
import glob

def plot_routing_distribution():
    results_dir = "../results"
    files = glob.glob(os.path.join(results_dir, "*_stats.csv"))
    
    if not files:
        return

    data = []
    for f in files:
        scenario = os.path.basename(f).replace("locust_", "").replace("_stats.csv", "")
        df = pd.read_csv(f)
        
        # Look for custom events
        cloud_reqs = df[df["Name"] == "Routed to cloud"]["Request Count"].values
        edge_reqs = df[df["Name"] == "Routed to edge"]["Request Count"].values
        
        c_count = cloud_reqs[0] if len(cloud_reqs) > 0 else 0
        e_count = edge_reqs[0] if len(edge_reqs) > 0 else 0
        
        if c_count + e_count > 0:
            data.append({"Scenario": scenario, "Cloud": c_count, "Edge": e_count})

    if not data:
        print("No routing data found.")
        return

    df_plot = pd.DataFrame(data).set_index("Scenario")
    
    # Normalize to percentages
    df_pct = df_plot.div(df_plot.sum(axis=1), axis=0) * 100

    ax = df_pct.plot(kind='bar', stacked=True, figsize=(10, 6), color=['#1f77b4', '#ff7f0e'])
    plt.title("Routing Distribution per Scenario (Cloud vs Edge)")
    plt.ylabel("Percentage (%)")
    plt.xticks(rotation=45)
    plt.legend(title="Site", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    os.makedirs("plots", exist_ok=True)
    plt.savefig("plots/routing_distribution.png")
    print("Saved plots/routing_distribution.png")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    plot_routing_distribution()
