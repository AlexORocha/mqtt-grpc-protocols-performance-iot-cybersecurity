"""
Payload Size vs Latency Analysis

This script analyzes the relationship between payload size and latency
for MQTT and gRPC protocols with/without TLS.

Usage:
    python analyze_payload.py
    
Requirements:
    - pandas
    - matplotlib
    - seaborn
    - psycopg2
    - scipy (optional, for statistical tests)
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import psycopg2
from datetime import datetime

# Set style
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)

# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "iotlab"),
            user=os.getenv("DB_USER", "iot"),
            password=os.getenv("DB_PASSWORD", "iot"),
            port=os.getenv("DB_PORT", "5433")
        )
        print("✅ Connected to database")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

# ==========================================================
# DATA LOADING
# ==========================================================

def load_data(conn):
    """Load message logs from database"""
    query = """
        SELECT 
            protocol,
            use_tls,
            temperature,
            humidity,
            current,
            client_timestamp,
            server_timestamp,
            latency_ms,
            payload_size_bytes,
            created_at
        FROM message_logs
        ORDER BY created_at
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        print(f"✅ Loaded {len(df)} records")
        return df
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        sys.exit(1)

# ==========================================================
# DATA PREPARATION
# ==========================================================

def prepare_data(df):
    """Prepare and clean data for analysis"""
    # Create scenario label
    df['scenario'] = df.apply(
        lambda row: f"{row['protocol'].upper()}_{'TLS' if row['use_tls'] else 'Plain'}", 
        axis=1
    )
    
    # Convert timestamps to datetime
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Create payload size categories
    df['payload_category'] = pd.cut(
        df['payload_size_bytes'],
        bins=[0, 500, 1000, 2000, 5000, float('inf')],
        labels=['<500B', '500B-1KB', '1KB-2KB', '2KB-5KB', '>5KB']
    )
    
    # Calculate latency in different units
    df['latency_us'] = df['latency_ms'] * 1000  # microseconds
    df['latency_s'] = df['latency_ms'] / 1000   # seconds
    
    # Calculate throughput (messages per second)
    df = df.sort_values('client_timestamp')
    df['time_diff'] = df.groupby('scenario')['client_timestamp'].diff()
    
    print(f"\n📊 Data Summary:")
    print(f"   Total records: {len(df)}")
    print(f"   Scenarios: {df['scenario'].unique()}")
    print(f"   Payload size range: {df['payload_size_bytes'].min()}-{df['payload_size_bytes'].max()} bytes")
    print(f"   Latency range: {df['latency_ms'].min():.2f}-{df['latency_ms'].max():.2f} ms")
    
    return df

# ==========================================================
# STATISTICAL ANALYSIS
# ==========================================================

def compute_statistics(df):
    """Compute statistical summaries"""
    stats = df.groupby(['scenario', 'payload_category']).agg({
        'latency_ms': ['count', 'mean', 'std', 'min', 'median', 'max'],
        'payload_size_bytes': ['mean', 'min', 'max']
    }).round(2)
    
    print("\n📈 Statistics by Scenario and Payload Size:")
    print(stats)
    
    # Overall statistics by scenario
    overall = df.groupby('scenario').agg({
        'latency_ms': ['count', 'mean', 'std', 'min', 'median', 'max'],
        'payload_size_bytes': ['mean', 'min', 'max']
    }).round(2)
    
    print("\n📊 Overall Statistics by Scenario:")
    print(overall)
    
    return stats, overall

def compute_correlation(df):
    """Compute correlation between payload size and latency"""
    print("\n🔗 Correlation Analysis (Payload Size vs Latency):")
    
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario]
        correlation = scenario_df['payload_size_bytes'].corr(scenario_df['latency_ms'])
        print(f"   {scenario}: {correlation:.4f}")
    
    # Overall correlation
    overall_corr = df['payload_size_bytes'].corr(df['latency_ms'])
    print(f"   Overall: {overall_corr:.4f}")

# ==========================================================
# VISUALIZATION
# ==========================================================

def plot_latency_vs_payload_scatter(df, output_dir):
    """Scatter plot: Latency vs Payload Size"""
    plt.figure(figsize=(14, 8))
    
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario]
        plt.scatter(
            scenario_df['payload_size_bytes'],
            scenario_df['latency_ms'],
            alpha=0.5,
            s=20,
            label=scenario
        )
    
    plt.xlabel('Payload Size (bytes)', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency vs Payload Size by Protocol', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'latency_vs_payload_scatter.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

def plot_latency_by_category(df, output_dir):
    """Box plot: Latency by Payload Category"""
    plt.figure(figsize=(14, 8))
    
    sns.boxplot(
        data=df,
        x='payload_category',
        y='latency_ms',
        hue='scenario'
    )
    
    plt.xlabel('Payload Size Category', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency Distribution by Payload Size Category', fontsize=14, fontweight='bold')
    plt.legend(title='Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'latency_by_category_boxplot.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

def plot_avg_latency_by_category(df, output_dir):
    """Bar plot: Average Latency by Category"""
    plt.figure(figsize=(14, 8))
    
    avg_latency = df.groupby(['scenario', 'payload_category'])['latency_ms'].mean().reset_index()
    
    sns.barplot(
        data=avg_latency,
        x='payload_category',
        y='latency_ms',
        hue='scenario'
    )
    
    plt.xlabel('Payload Size Category', fontsize=12)
    plt.ylabel('Average Latency (ms)', fontsize=12)
    plt.title('Average Latency by Payload Size Category', fontsize=14, fontweight='bold')
    plt.legend(title='Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'avg_latency_by_category.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

def plot_latency_per_byte(df, output_dir):
    """Plot: Latency per Byte (Protocol Efficiency)"""
    plt.figure(figsize=(14, 8))
    
    # Calculate latency per byte
    df['latency_per_byte'] = df['latency_ms'] / df['payload_size_bytes']
    
    avg_efficiency = df.groupby(['scenario', 'payload_category'])['latency_per_byte'].mean().reset_index()
    
    sns.barplot(
        data=avg_efficiency,
        x='payload_category',
        y='latency_per_byte',
        hue='scenario'
    )
    
    plt.xlabel('Payload Size Category', fontsize=12)
    plt.ylabel('Latency per Byte (ms/byte)', fontsize=12)
    plt.title('Protocol Efficiency: Latency per Byte', fontsize=14, fontweight='bold')
    plt.legend(title='Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'latency_per_byte.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

def plot_regression_lines(df, output_dir):
    """Scatter with regression: Latency vs Payload"""
    plt.figure(figsize=(14, 8))
    
    sns.lmplot(
        data=df,
        x='payload_size_bytes',
        y='latency_ms',
        hue='scenario',
        height=8,
        aspect=1.5,
        scatter_kws={'alpha': 0.3, 's': 20},
        line_kws={'linewidth': 2}
    )
    
    plt.xlabel('Payload Size (bytes)', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency vs Payload Size (with Linear Regression)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'latency_vs_payload_regression.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

def plot_heatmap(df, output_dir):
    """Heatmap: Average Latency Matrix"""
    plt.figure(figsize=(10, 6))
    
    # Pivot table for heatmap
    pivot = df.pivot_table(
        values='latency_ms',
        index='payload_category',
        columns='scenario',
        aggfunc='mean'
    )
    
    sns.heatmap(
        pivot,
        annot=True,
        fmt='.2f',
        cmap='YlOrRd',
        cbar_kws={'label': 'Latency (ms)'}
    )
    
    plt.title('Average Latency Heatmap (ms)', fontsize=14, fontweight='bold')
    plt.ylabel('Payload Size Category', fontsize=12)
    plt.xlabel('Scenario', fontsize=12)
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'latency_heatmap.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

def plot_time_series(df, output_dir):
    """Time series: Latency over time"""
    plt.figure(figsize=(16, 8))
    
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario].sort_values('created_at')
        plt.plot(
            scenario_df['created_at'],
            scenario_df['latency_ms'],
            alpha=0.6,
            label=scenario,
            linewidth=0.5
        )
    
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency Over Time by Protocol', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, 'latency_timeseries.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {filepath}")
    plt.close()

# ==========================================================
# EXPORT RESULTS
# ==========================================================

def export_statistics(df, output_dir):
    """Export statistics to CSV"""
    # Summary by scenario and category
    summary = df.groupby(['scenario', 'payload_category']).agg({
        'latency_ms': ['count', 'mean', 'std', 'min', 'median', 'max'],
        'payload_size_bytes': ['mean', 'min', 'max']
    }).round(2)
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    
    filepath = os.path.join(output_dir, 'payload_latency_summary.csv')
    summary.to_csv(filepath)
    print(f"✅ Saved: {filepath}")
    
    # Detailed data export
    export_cols = [
        'scenario', 'protocol', 'use_tls', 'payload_size_bytes',
        'payload_category', 'latency_ms', 'created_at'
    ]
    detailed_filepath = os.path.join(output_dir, 'payload_latency_detailed.csv')
    df[export_cols].to_csv(detailed_filepath, index=False)
    print(f"✅ Saved: {detailed_filepath}")

# ==========================================================
# MAIN
# ==========================================================

def main():
    print("=" * 60)
    print("  PAYLOAD SIZE vs LATENCY ANALYSIS")
    print("=" * 60)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'results', 'payload_analysis')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📂 Output directory: {output_dir}")
    
    # Connect to database
    conn = connect_db()
    
    # Load data
    df = load_data(conn)
    
    if len(df) == 0:
        print("⚠️  No data found in database. Run experiments first.")
        conn.close()
        return
    
    # Prepare data
    df = prepare_data(df)
    
    # Statistical analysis
    stats, overall = compute_statistics(df)
    compute_correlation(df)
    
    # Generate visualizations
    print("\n📊 Generating visualizations...")
    plot_latency_vs_payload_scatter(df, output_dir)
    plot_latency_by_category(df, output_dir)
    plot_avg_latency_by_category(df, output_dir)
    plot_latency_per_byte(df, output_dir)
    plot_regression_lines(df, output_dir)
    plot_heatmap(df, output_dir)
    plot_time_series(df, output_dir)
    
    # Export results
    print("\n💾 Exporting statistics...")
    export_statistics(df, output_dir)
    
    # Close connection
    conn.close()
    
    print("\n" + "=" * 60)
    print("  ✅ ANALYSIS COMPLETE!")
    print(f"     Results saved to: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
