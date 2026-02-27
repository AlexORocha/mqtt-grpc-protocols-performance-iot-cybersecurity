"""
IEEE-Style Payload Comparison Plot
MQTT vs gRPC (TLS)

Generates publication-ready figure similar to academic articles.

Usage:
    python analyze_payload_ieee.py
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2

# ==========================================================
# MATPLOTLIB STYLE (IEEE-like)
# ==========================================================

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.figsize": (7, 3.5),  # IEEE single-column width
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
# LOAD TLS DATA
# ==========================================================

def load_tls_data(conn):
    query = """
        SELECT protocol,
               payload_size_bytes,
               created_at
        FROM message_logs
        WHERE use_tls = true
        ORDER BY created_at
    """
    return pd.read_sql_query(query, conn)

# ==========================================================
# GENERATE PLOT
# ==========================================================

def generate_ieee_plot(df, output_path):

    if df.empty:
        print("No TLS data found.")
        return

    mqtt_df = df[df["protocol"] == "mqtt"].copy()
    grpc_df = df[df["protocol"] == "grpc"].copy()

    mqtt_df["seq"] = range(1, len(mqtt_df) + 1)
    grpc_df["seq"] = range(1, len(grpc_df) + 1)

    fig, ax = plt.subplots()

    # MQTT line (blue)
    if not mqtt_df.empty:
        ax.plot(
            mqtt_df["seq"],
            mqtt_df["payload_size_bytes"],
            color="tab:blue",
            linewidth=1.2,
            label="MQTT"
        )

    # gRPC line (red)
    if not grpc_df.empty:
        ax.plot(
            grpc_df["seq"],
            grpc_df["payload_size_bytes"],
            color="tab:red",
            linewidth=1.2,
            label="gRPC"
        )

    ax.set_xlabel("Message Sequence Number")
    ax.set_ylabel("Payload Envelope (bytes)")
    ax.set_title("Payload MQTT vs gRPC (TLS)")
    ax.legend(frameon=False)

    plt.tight_layout()

    plt.savefig(output_path, dpi=600, bbox_inches="tight")
    print(f"Figure saved at: {output_path}")

    plt.show()

# ==========================================================
# MAIN
# ==========================================================

def main():

    output_dir = os.path.join(
        os.path.dirname(__file__),
        "results",
        "ieee_figures"
    )
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(
        output_dir,
        "figure_payload_mqtt_vs_grpc_tls.png"
    )

    conn = connect_db()
    df = load_tls_data(conn)
    conn.close()

    print(f"Loaded {len(df)} TLS records")

    generate_ieee_plot(df, output_path)


if __name__ == "__main__":
    main()