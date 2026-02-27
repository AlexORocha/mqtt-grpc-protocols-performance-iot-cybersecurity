import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import subprocess
import os
from scipy.stats import ttest_ind

# =========================
# LOAD DATA
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")

files = glob.glob(os.path.join(RESULTS_DIR, "*.csv"))

if not files:
    print("No CSV files found in:", RESULTS_DIR)
    exit()

df_list = [pd.read_csv(f) for f in files]
df = pd.concat(df_list)

df["scenario"] = df["protocol"] + "_TLS_" + df["use_tls"].astype(str)

grouped = df.groupby("scenario")

# =========================
# LATENCY METRICS
# =========================

summary = grouped["latency_ms"].agg([
    "count",
    "mean",
    "median",
    "std",
    "min",
    "max"
])

summary["p95"] = grouped["latency_ms"].quantile(0.95)
summary["p99"] = grouped["latency_ms"].quantile(0.99)
summary["p999"] = grouped["latency_ms"].quantile(0.999)
summary["coef_variation"] = summary["std"] / summary["mean"]

print("\n=== LATENCY SUMMARY ===")
print(summary)

# =========================
# PAYLOAD
# =========================

payload_summary = grouped["payload_size_bytes"].agg([
    "mean",
    "std",
    "min",
    "max"
])

print("\n=== PAYLOAD SUMMARY ===")
print(payload_summary)

# =========================
# THROUGHPUT
# =========================

throughput = grouped["server_timestamp"].agg(
    lambda x: len(x) / (x.max() - x.min())
)

print("\n=== THROUGHPUT (msg/sec) ===")
print(throughput)

# =========================
# HANDSHAKE COST
# =========================

df_sorted = df.sort_values("server_timestamp")
first_messages = df_sorted.groupby("scenario").head(1)

print("\n=== HANDSHAKE LATENCY ===")
print(first_messages[["scenario","latency_ms"]])

# =========================
# STATISTICAL TEST (Welch)
# =========================

try:
    mqtt_tls = df[(df.protocol=="mqtt") & (df.use_tls==True)]["latency_ms"]
    grpc_tls = df[(df.protocol=="grpc") & (df.use_tls==True)]["latency_ms"]

    t_stat, p_value = ttest_ind(mqtt_tls, grpc_tls, equal_var=False)

    print("\n=== Welch T-Test (MQTT TLS vs gRPC TLS) ===")
    print("t-stat:", t_stat)
    print("p-value:", p_value)
except:
    print("\nStatistical comparison skipped (insufficient data).")

# =========================
# CLIFF'S DELTA
# =========================

def cliffs_delta(a, b):
    n = len(a)
    m = len(b)
    greater = sum(x > y for x in a for y in b)
    lesser = sum(x < y for x in a for y in b)
    return (greater - lesser) / (n * m)

try:
    delta = cliffs_delta(mqtt_tls.values, grpc_tls.values)
    print("\n=== Cliff's Delta ===")
    print(delta)
except:
    pass

# =========================
# WIRE SIZE (PCAP)
# =========================

print("\n=== WIRE SIZE ANALYSIS ===")

if os.path.exists("captures/capture.pcap"):
    try:
        result = subprocess.run(
            ["tshark", "-r", "captures/capture.pcap",
             "-T", "fields", "-e", "frame.len"],
            capture_output=True,
            text=True
        )

        sizes = [int(x) for x in result.stdout.split() if x.isdigit()]

        if sizes:
            print("Mean wire size:", np.mean(sizes))
            print("p95 wire size:", np.percentile(sizes, 95))
            print("Max wire size:", max(sizes))
    except:
        print("tshark not found or error reading pcap.")
else:
    print("No capture.pcap found.")

# =========================
# PLOTS
# =========================

sns.set(style="whitegrid")

fig, axes = plt.subplots(2, 2, figsize=(16,12))

sns.boxplot(
    data=df,
    x="scenario",
    y="latency_ms",
    ax=axes[0,0]
)
axes[0,0].set_title("Latency Distribution")

summary["p95"].plot(kind="bar", ax=axes[0,1])
axes[0,1].set_title("p95 Latency")

payload_summary["mean"].plot(kind="bar", ax=axes[1,0])
axes[1,0].set_title("Mean Payload Size")

throughput.plot(kind="bar", ax=axes[1,1])
axes[1,1].set_title("Throughput (msg/sec)")

plt.tight_layout()
plt.savefig("comparison.png")
plt.show()

# =========================
# EXPORT SUMMARY
# =========================

summary.to_csv("latency_summary.csv")
payload_summary.to_csv("payload_summary.csv")

print("\nAnalysis complete. Files generated:")
print("- comparison.png")
print("- latency_summary.csv")
print("- payload_summary.csv")