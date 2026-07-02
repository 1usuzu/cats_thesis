import glob
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Paths
RESULTS_DIR = Path(__file__).parent / "results"
ARTIFACTS_DIR = Path("/home/lusuzu/.gemini/antigravity-ide/brain/ac3d29ab-10a6-44dc-9b9b-3e7881c4d1b1")

def plot_results():
    summary_csv = RESULTS_DIR / "final_benchmark_summary.csv"
    if not summary_csv.exists():
        print("Summary CSV not found. Run merge_results.py first.")
        return

    df = pd.read_csv(summary_csv)
    
    # Set seaborn style for premium look
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["font.family"] = "sans-serif"
    
    # 1. Latency Comparison
    plt.figure(figsize=(14, 8))
    # Filter to show P95 latency across profiles for HIGH load
    df_high = df[df["Load"] == "high"]
    ax = sns.barplot(data=df_high, x="Profile", y="P95_Latency", hue="Strategy", palette="viridis")
    plt.title("P95 Latency Comparison Under High Load", pad=20, fontsize=18, fontweight="bold")
    plt.ylabel("P95 Latency (ms)", fontsize=14)
    plt.xlabel("Network Profile", fontsize=14)
    plt.legend(title="Strategy", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "latency_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()

    # 2. SLA / Failure Violations
    plt.figure(figsize=(14, 8))
    ax = sns.barplot(data=df_high, x="Profile", y="Fail_Rate_%", hue="Strategy", palette="rocket")
    plt.title("Failure & SLA Miss Rate Under High Load", pad=20, fontsize=18, fontweight="bold")
    plt.ylabel("Failure Rate (%)", fontsize=14)
    plt.xlabel("Network Profile", fontsize=14)
    plt.legend(title="Strategy", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(ARTIFACTS_DIR / "sla_violations.png", dpi=300, bbox_inches="tight")
    plt.close()

    # 3. Routing Distribution (Only for PROPOSED strategy across profiles)
    routing_data = []
    stats_files = glob.glob(str(RESULTS_DIR / "benchmark_*_*_PROPOSED_stats.csv"))
    
    for f in stats_files:
        basename = os.path.basename(f)
        parts = basename.replace("benchmark_", "").replace("_stats.csv", "").split("_")
        if len(parts) >= 3:
            profile = parts[0]
            load = parts[1]
            if load != "high":
                continue # only show high load
                
            try:
                sdf = pd.read_csv(f)
                route_rows = sdf[sdf["Type"].str.contains("ROUTE", na=False)]
                cloud_count = 0
                edge_count = 0
                fallback_count = 0
                
                for _, row in route_rows.iterrows():
                    name = row["Name"]
                    count = row["Request Count"]
                    if "cloud" in name.lower() and "fallback" not in name.lower():
                        cloud_count += count
                    elif "edge" in name.lower() and "fallback" not in name.lower():
                        edge_count += count
                    elif "fallback" in name.lower():
                        fallback_count += count
                        
                total = cloud_count + edge_count + fallback_count
                if total > 0:
                    routing_data.append({
                        "Profile": profile.capitalize(),
                        "Cloud (%)": (cloud_count / total) * 100,
                        "Edge (%)": (edge_count / total) * 100,
                        "Fallback (%)": (fallback_count / total) * 100
                    })
            except Exception as e:
                print(f"Error parsing routing for {f}: {e}")

    if routing_data:
        r_df = pd.DataFrame(routing_data)
        r_df.set_index("Profile", inplace=True)
        # Sort index if possible (Good, Medium, Bad)
        order = [x for x in ["Good", "Medium", "Bad"] if x in r_df.index]
        r_df = r_df.loc[order]
        
        ax = r_df.plot(kind="bar", stacked=True, figsize=(12, 8), colormap="crest")
        plt.title("Routing Decision Distribution (PROPOSED Strategy, High Load)", pad=20, fontsize=18, fontweight="bold")
        plt.ylabel("Percentage of Requests (%)", fontsize=14)
        plt.xlabel("Network Profile", fontsize=14)
        plt.legend(title="Route Target", bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=0)
        
        # Add percentage labels
        for c in ax.containers:
            ax.bar_label(c, fmt='%.1f%%', label_type='center', color='white', weight='bold')
            
        plt.tight_layout()
        plt.savefig(ARTIFACTS_DIR / "routing_distribution.png", dpi=300, bbox_inches="tight")
        plt.close()
    
    print(f"✅ Charts generated successfully in {ARTIFACTS_DIR}")

if __name__ == "__main__":
    plot_results()
