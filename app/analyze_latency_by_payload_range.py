"""
Latency vs Payload Size Range (Academic Version)

Compares average latency by payload size bucket (10KB–50KB)
Across:
- MQTT Plain
- MQTT TLS
- gRPC Plain
- gRPC TLS

Generates IEEE-style publication-ready figure.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2

# ==========================================================
# IEEE STYLE CONFIG
# ==========================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.figsize": (7, 4),   # IEEE single column
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def connect_db():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "iotlab"),
            user=os.getenv("DB_USER", "iot"),
            password=os.getenv("DB_PASSWORD", "iot"),
            port=os.getenv("DB_PORT", "5433")
        )
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)

# ==========================================================
# LOAD DATA
# ==========================================================

def load_data(conn):
    query = """
        SELECT protocol,
               use_tls,
               latency_ms,
               payload_size_before_bytes
        FROM message_logs
        WHERE payload_size_before_bytes BETWEEN 10000 AND 50000
    """
    return pd.read_sql_query(query, conn)

# ==========================================================
# PREPARE DATA
# ==========================================================

def prepare_data(df):

    df["payload_kb"] = df["payload_size_before_bytes"] / 1024

    bins = [10, 20, 30, 40, 50]
    labels = ["10–20KB", "20–30KB", "30–40KB", "40–50KB"]

    df["payload_range"] = pd.cut(
        df["payload_kb"],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    df["scenario"] = df.apply(
        lambda row: f"{row['protocol'].upper()} {'TLS' if row['use_tls'] else 'Plain'}",
        axis=1
    )

    return df

# ==========================================================
# COMPUTE STATISTICS (WITH 95% CI)
# ==========================================================

def compute_stats(df):

    grouped = df.groupby(["scenario", "payload_range"])

    stats = grouped["latency_ms"].agg(["mean", "std", "count"]).reset_index()

    # 95% confidence interval
    stats["ci95"] = 1.96 * (stats["std"] / np.sqrt(stats["count"]))

    return stats

# ==========================================================
# PLOT
# ==========================================================

def plot_latency(stats):

    scenarios_order = [
        "MQTT Plain",
        "MQTT TLS",
        "GRPC Plain",
        "GRPC TLS"
    ]

    payload_order = ["10–20KB", "20–30KB", "30–40KB", "40–50KB"]

    stats["scenario"] = pd.Categorical(stats["scenario"], scenarios_order)
    stats["payload_range"] = pd.Categorical(stats["payload_range"], payload_order)

    stats = stats.sort_values(["payload_range", "scenario"])

    fig, ax = plt.subplots()

    width = 0.2
    x = np.arange(len(payload_order))

    colors = {
        "MQTT Plain": "#1f77b4",
        "MQTT TLS": "#4c9ed9",
        "GRPC Plain": "#d62728",
        "GRPC TLS": "#ff6b6b"
    }

    for i, scenario in enumerate(scenarios_order):
        subset = stats[stats["scenario"] == scenario]
        ax.bar(
            x + (i - 1.5) * width,
            subset["mean"],
            width=width,
            yerr=subset["ci95"],
            capsize=3,
            label=scenario,
            color=colors[scenario],
            edgecolor="black",
            linewidth=0.5
        )

    ax.set_xticks(x)
    ax.set_xticklabels(payload_order)
    ax.set_xlabel("Payload Size Range")
    ax.set_ylabel("Average Latency (ms)")
    ax.set_title("Latency vs Payload Size (10–50KB)")
    ax.legend(frameon=False)

    plt.tight_layout()

    os.makedirs("results/ieee_figures", exist_ok=True)
    plt.savefig("results/ieee_figures/latency_by_payload_range_ieee.png",
                dpi=600, bbox_inches="tight")
    plt.savefig("results/ieee_figures/latency_by_payload_range_ieee.pdf",
                bbox_inches="tight")

    plt.show()

# ==========================================================
# MAIN
# ==========================================================

def main():

    conn = connect_db()
    df = load_data(conn)
    conn.close()

    if df.empty:
        print("No data in 10KB–50KB range.")
        return

    df = prepare_data(df)
    stats = compute_stats(df)

    print("\nLatency by Payload Range (with 95% CI):")
    print(stats)

    plot_latency(stats)

if __name__ == "__main__":
    main()