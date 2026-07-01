import glob
import os
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).parent / "results"

def merge_results():
    stats_files = glob.glob(str(RESULTS_DIR / "*_stats.csv"))

    summary_data = []

    for f in stats_files:
        # Expected format: benchmark_{profile}_{load}_{strategy}_stats.csv
        basename = os.path.basename(f)
        parts = basename.replace("benchmark_", "").replace("_stats.csv", "").split("_")
        if len(parts) >= 3:
            profile, load, strategy = parts[0], parts[1], "_".join(parts[2:])

            try:
                df = pd.read_csv(f)
                # Locust summary row is usually named "Aggregated"
                agg_row = df[df["Name"] == "Aggregated"]
                if not agg_row.empty:
                    reqs = agg_row["Request Count"].values[0]
                    fails = agg_row["Failure Count"].values[0]
                    p95 = agg_row["95%"].values[0]
                    p99 = agg_row["99%"].values[0]

                    fail_rate = (fails / reqs * 100) if reqs > 0 else 0

                    summary_data.append({
                        "Profile": profile,
                        "Load": load,
                        "Strategy": strategy,
                        "Requests": reqs,
                        "Failures": fails,
                        "Fail_Rate_%": round(fail_rate, 2),
                        "P95_Latency": p95,
                        "P99_Latency": p99
                    })
            except Exception as e:
                print(f"Error reading {f}: {e}")

    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values(by=["Profile", "Load", "Strategy"])
        out_csv = RESULTS_DIR / "final_benchmark_summary.csv"
        summary_df.to_csv(out_csv, index=False)
        print(f"✅ Merged summary saved to {out_csv}")
        print("\n=== Benchmark Summary ===")
        print(summary_df.to_markdown(index=False))
    else:
        print("No valid stats files found to merge.")

if __name__ == "__main__":
    merge_results()
