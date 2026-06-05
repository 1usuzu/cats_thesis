#!/usr/bin/env python3
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

RESULTS_DIR = "benchmark/results"
PLOTS_DIR = "analysis/plots"
SLA_MS = 2000

def estimate_sla_violations(row):
    """
    Estimates the number of SLA violations based on percentile data + failures.
    """
    try:
        reqs = float(row.get('Request Count', 0))
        fail_count = float(row.get('Failure Count', 0))
        if pd.isna(reqs) or reqs <= 0: return fail_count
        
        slow_reqs = 0
        if float(row.get('50%', 0)) > SLA_MS: slow_reqs = reqs * 0.50
        elif float(row.get('66%', 0)) > SLA_MS: slow_reqs = reqs * 0.34
        elif float(row.get('75%', 0)) > SLA_MS: slow_reqs = reqs * 0.25
        elif float(row.get('80%', 0)) > SLA_MS: slow_reqs = reqs * 0.20
        elif float(row.get('90%', 0)) > SLA_MS: slow_reqs = reqs * 0.10
        elif float(row.get('95%', 0)) > SLA_MS: slow_reqs = reqs * 0.05
        elif float(row.get('98%', 0)) > SLA_MS: slow_reqs = reqs * 0.02
        elif float(row.get('99%', 0)) > SLA_MS: slow_reqs = reqs * 0.01
        elif float(row.get('Max Response Time', 0)) > SLA_MS: slow_reqs = 1
        
        # Total violations = slow requests + failed requests (capped at total reqs)
        return min(reqs, slow_reqs + fail_count)
    except ValueError:
        pass
    return float(row.get('Failure Count', 0))

def generate_plots():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    
    files = glob.glob(os.path.join(RESULTS_DIR, "benchmark_*_*_*_stats.csv"))
    if not files:
        print(f"Error: No CSV files found in {RESULTS_DIR} matching pattern 'benchmark_{{profile}}_{{load}}_{{strategy}}_stats.csv'.")
        return

    records = []
    pattern = re.compile(r"benchmark_([^_]+)_([^_]+)_([^_]+)_stats\.csv")
    
    for filepath in files:
        filename = os.path.basename(filepath)
        match = pattern.match(filename)
        if not match:
            continue
            
        profile, load, strategy = match.groups()
        
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue
            
        if df.empty or "Name" not in df.columns:
            print(f"Warning: {filepath} is empty or missing expected columns.")
            continue
            
        # Overall stats from Aggregated row
        agg_row = df[df["Name"] == "Aggregated"]
        if agg_row.empty:
            continue
        agg_row = agg_row.iloc[0]
        
        req_count = float(agg_row.get("Request Count", 0))
        fail_count = float(agg_row.get("Failure Count", 0))
        p99_latency = float(agg_row.get("99%", 0))
        
        # 100% Failure detection
        catastrophic = (req_count > 0 and req_count == fail_count)
        
        sla_violations = estimate_sla_violations(agg_row)
        
        # Debug print for BAD profile
        if profile.upper() == "BAD":
            max_resp = float(agg_row.get("Max Response Time", 0))
            print(f"[DEBUG] Profile: {profile.upper()} | Strategy: {strategy} | Load: {load}")
            print(f"        Max Response Time: {max_resp} ms | Estimated SLA Violations: {sla_violations}")
        
        # Extract custom routing events
        cloud_reqs = 0
        edge_reqs = 0
        
        cloud_row = df[df["Name"] == "Routed to cloud"]
        if not cloud_row.empty:
            cloud_reqs = float(cloud_row.iloc[0].get("Request Count", 0))
            
        edge_row = df[df["Name"] == "Routed to edge"]
        if not edge_row.empty:
            edge_reqs = float(edge_row.iloc[0].get("Request Count", 0))
            
        records.append({
            "Strategy": strategy.upper(),
            "Profile": profile.upper(),
            "Load": load.upper(),
            "P99_Latency": p99_latency,  # Removed 0 if catastrophic so error latency is plotted
            "SLA_Violations": sla_violations,
            "Cloud_Routes": cloud_reqs,
            "Edge_Routes": edge_reqs,
            "Failed_Routes": max(0, req_count - cloud_reqs - edge_reqs), # Track unrouted failures
            "Catastrophic": catastrophic
        })

    if not records:
        print("Error: No valid data extracted from the CSV files.")
        return
        
    data = pd.DataFrame(records)
    
    # ---------------------------------------------------------
    # Plot 1: Latency Comparison
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    ax1 = sns.barplot(data=data, x="Profile", y="P99_Latency", hue="Strategy", errorbar=None)
    plt.title("P99 Response Time by Network Profile and Strategy", fontsize=14, pad=15)
    plt.ylabel("P99 Latency (ms)", weight='bold')
    plt.xlabel("Network Profile", weight='bold')
            
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "latency_comparison.png"), dpi=300)
    plt.close()
    
    # ---------------------------------------------------------
    # Plot 2: SLA Violations
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    ax2 = sns.barplot(data=data, x="Profile", y="SLA_Violations", hue="Strategy", errorbar=None)
    plt.title("Estimated SLA Violations by Network Profile", fontsize=14, pad=15)
    plt.ylabel("Number of SLA Violations (>2000ms)", weight='bold')
    plt.xlabel("Network Profile", weight='bold')
    
    # Draw a line at 0 for visual grounding
    plt.axhline(0, color='black', linewidth=1)
            
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "sla_violations.png"), dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Plot 3: Routing Distribution (PROPOSED only)
    # ---------------------------------------------------------
    prop_data = data[data["Strategy"] == "PROPOSED"].copy()
    if not prop_data.empty:
        # Aggregate by load across profiles (or you can group by profile+load)
        route_agg = prop_data.groupby("Load")[["Cloud_Routes", "Edge_Routes", "Failed_Routes"]].sum()
        
        # Calculate percentages
        row_sums = route_agg.sum(axis=1)
        # Avoid division by zero
        route_pct = route_agg.div(row_sums.replace(0, 1), axis=0) * 100
        
        ax3 = route_pct.plot(kind="bar", stacked=True, figsize=(8, 6), color=["#3498db", "#2ecc71", "#e74c3c"], edgecolor="white")
        plt.title("Routing Distribution for PROPOSED Strategy", fontsize=14, pad=15)
        plt.ylabel("Percentage of Requests (%)", weight='bold')
        plt.xlabel("Load Level", weight='bold')
        plt.legend(["Cloud", "Edge", "Failed"], loc='upper right', frameon=True)
        plt.xticks(rotation=0)
        
        # Add percentage labels
        for c in ax3.containers:
            ax3.bar_label(c, fmt='%.1f%%', label_type='center', color='white', weight='bold')
            
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, "routing_distribution.png"), dpi=300)
        plt.close()
        print(f"Successfully generated plots in {PLOTS_DIR}/")
    else:
        print("Warning: No data found for PROPOSED strategy to generate routing distribution.")

if __name__ == "__main__":
    generate_plots()
