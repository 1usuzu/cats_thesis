import pandas as pd
import os
import glob

def export_summary_table():
    results_dir = "../results"
    files = glob.glob(os.path.join(results_dir, "*_stats.csv"))
    
    if not files:
        return

    data = []
    for f in files:
        scenario = os.path.basename(f).replace("locust_", "").replace("_stats.csv", "")
        df = pd.read_csv(f)
        
        row = df[df["Name"] == "/v1/chat"]
        if not row.empty:
            data.append({
                "Scenario": scenario,
                "Total Requests": row["Request Count"].values[0],
                "Failures": row["Failure Count"].values[0],
                "Avg RT (ms)": row["Average Response Time"].values[0],
                "P95 RT (ms)": row["95%"].values[0],
                "Max RT (ms)": row["Max Response Time"].values[0],
                "Avg RPS": row["Requests/s"].values[0]
            })

    if not data:
        return

    df_summary = pd.DataFrame(data).sort_values("Scenario")
    
    os.makedirs("tables", exist_ok=True)
    
    # Markdown
    with open("tables/summary.md", "w") as f:
        f.write(df_summary.to_markdown(index=False))
        
    # LaTeX
    with open("tables/summary.tex", "w") as f:
        f.write(df_summary.to_latex(index=False, float_format="%.2f"))
        
    print("Exported tables/summary.md and tables/summary.tex")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    export_summary_table()
