import os
import glob
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind

# ==========================================================
# CONFIG
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")

sns.set(style="whitegrid")

# ==========================================================
# LOAD FILES
# ==========================================================

csv_files = glob.glob(os.path.join(RESULTS_DIR, "results_*.csv"))
csv_files = [f for f in csv_files if not f.endswith("_stats.csv")]

if not csv_files:
    print("No CSV files found.")
    exit()

df_list = []

for file in csv_files:
    scenario = os.path.basename(file).replace(".csv", "")
    data = pd.read_csv(file)

    if "client_timestamp" not in data.columns or "server_timestamp" not in data.columns:
        continue

    data["scenario"] = scenario
    data["latency_ms"] = data["server_timestamp"] - data["client_timestamp"]

    df_list.append(data)

df = pd.concat(df_list, ignore_index=True)
df = df.reset_index(drop=True)

# ==========================================================
# METRICS
# ==========================================================

throughput = df.groupby("scenario")["server_timestamp"].agg(
    lambda x: len(x) / (x.max() - x.min())
)

def extract_protocol(name):
    if "mqtt" in name.lower():
        return "MQTT"
    if "grpc" in name.lower():
        return "gRPC"
    return "Unknown"

def extract_security(name):
    if "tls_t" in name.lower():
        return "TLS"
    if "tls_f" in name.lower():
        return "Plain"
    return "Unknown"

df["protocol"] = df["scenario"].apply(extract_protocol)
df["security"] = df["scenario"].apply(extract_security)

# ==========================================================
# FIGURE PANEL
# ==========================================================

fig, axes = plt.subplots(3, 2, figsize=(18, 14))
axes = axes.flatten()

# -----------------------------
# 1) Mean + Std
# -----------------------------

latency_stats = df.groupby("scenario")["latency_ms"].agg(["mean", "std"]).reset_index()

axes[0].bar(
    latency_stats["scenario"],
    latency_stats["mean"],
    yerr=latency_stats["std"],
    capsize=5
)
axes[0].set_title("Average Latency (ms)")
axes[0].set_ylabel("Latency (ms)")
axes[0].tick_params(axis='x', rotation=45)

# -----------------------------
# 2) CDF
# -----------------------------

for scenario in df["scenario"].unique():
    subset = df[df["scenario"] == scenario]["latency_ms"].sort_values()
    cdf = np.arange(len(subset)) / float(len(subset))
    axes[1].plot(subset, cdf, label=scenario)

axes[1].set_title("Latency CDF")
axes[1].set_xlabel("Latency (ms)")
axes[1].set_ylabel("CDF")
axes[1].legend()

# -----------------------------
# 3) Boxplot
# -----------------------------

sns.boxplot(data=df, x="scenario", y="latency_ms", ax=axes[2])
axes[2].set_title("Latency Distribution")
axes[2].tick_params(axis='x', rotation=45)

# -----------------------------
# 4) Throughput
# -----------------------------

throughput_df = throughput.reset_index()

axes[3].bar(
    throughput_df["scenario"],
    throughput_df["server_timestamp"]
)
axes[3].set_title("Throughput (msg/sec)")
axes[3].tick_params(axis='x', rotation=45)

# -----------------------------
# 5) TLS Overhead
# -----------------------------

overhead = df.groupby(["protocol", "security"])["latency_ms"].mean().unstack()

overhead.plot(kind="bar", ax=axes[4])
axes[4].set_title("TLS Overhead")
axes[4].set_ylabel("Average Latency (ms)")
axes[4].tick_params(axis='x', rotation=0)

# -----------------------------
# 6) Payload (if exists)
# -----------------------------

if "payload_size" in df.columns:
    payload_stats = df.groupby("scenario")["payload_size"].mean().reset_index()
    axes[5].bar(payload_stats["scenario"], payload_stats["payload_size"])
    axes[5].set_title("Average Payload Size")
    axes[5].tick_params(axis='x', rotation=45)
else:
    axes[5].axis("off")

plt.suptitle("MQTT vs gRPC Performance Comparison", fontsize=16)
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.show()

print("\nAll graphs rendered in a single window.")