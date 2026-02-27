"""
Payload Serialization Analysis v2

This script analyzes the overhead of serialization by comparing:
- payload_size_before_bytes: Original JSON payload size (before serialization)
- payload_size_bytes: Serialized payload size (MQTT JSON or gRPC Protobuf)

This reveals the efficiency of each protocol's serialization format.

Usage:
    python analyze_payload_v2.py
    
Requirements:
    - pandas
    - matplotlib
    - seaborn
    - psycopg2
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
    """Load message logs from database with payload size before serialization"""
    
    # First, check total records and column status
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM message_logs")
        total_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM message_logs WHERE payload_size_before_bytes IS NOT NULL")
        records_with_payload = cursor.fetchone()[0]
        
        cursor.close()
        
        print(f"\n📊 Database Status:")
        print(f"   Total records: {total_records}")
        print(f"   Records with payload_size_before: {records_with_payload}")
        
        if records_with_payload == 0 and total_records > 0:
            print("\n⚠️  WARNING: Database has records but payload_size_before_bytes is empty!")
            print("   This means the data was collected BEFORE enabling ANALYZE_PAYLOAD_BEFORE")
            print("\n💡 Solution:")
            print("   1. Clear the database: python clear_database.py")
            print("   2. Run experiments with payload analysis: ./run_experiments_with_payload.sh")
            print("\n   Or verify that ANALYZE_PAYLOAD_BEFORE=true is set in the environment")
            
    except Exception as e:
        print(f"⚠️  Could not check database status: {e}")
    
    # Load data
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
            payload_size_before_bytes,
            created_at
        FROM message_logs
        WHERE payload_size_before_bytes IS NOT NULL
        ORDER BY created_at
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        print(f"✅ Loaded {len(df)} records with payload analysis data")
            
        return df
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        sys.exit(1)

# ==========================================================
# DATA PREPARATION
# ==========================================================

def prepare_data(df):
    """Prepare and clean data for serialization analysis"""
    # Create scenario label
    df['scenario'] = df.apply(
        lambda row: f"{row['protocol'].upper()}_{'TLS' if row['use_tls'] else 'Plain'}", 
        axis=1
    )
    
    # Calculate serialization metrics
    df['serialization_overhead_bytes'] = df['payload_size_bytes'] - df['payload_size_before_bytes']
    df['serialization_overhead_percent'] = (
        (df['payload_size_bytes'] - df['payload_size_before_bytes']) / 
        df['payload_size_before_bytes'] * 100
    ).round(2)
    
    # Compression ratio (negative overhead means compression)
    df['compression_ratio'] = (
        df['payload_size_before_bytes'] / df['payload_size_bytes']
    ).round(3)
    
    # Create payload size categories
    df['payload_category'] = pd.cut(
        df['payload_size_before_bytes'],
        bins=[0, 500, 1000, 2000, 5000, float('inf')],
        labels=['<500B', '500B-1KB', '1KB-2KB', '2KB-5KB', '>5KB']
    )
    
    # Convert timestamps to datetime
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    print(f"\n📊 Data Summary:")
    print(f"   Total records: {len(df)}")
    print(f"   Scenarios: {df['scenario'].unique()}")
    print(f"   Payload size (before): {df['payload_size_before_bytes'].min()}-{df['payload_size_before_bytes'].max()} bytes")
    print(f"   Payload size (after): {df['payload_size_bytes'].min()}-{df['payload_size_bytes'].max()} bytes")
    
    return df

# ==========================================================
# STATISTICAL ANALYSIS
# ==========================================================

def compute_serialization_stats(df):
    """Compute serialization overhead statistics"""
    print("\n" + "=" * 70)
    print("  SERIALIZATION OVERHEAD ANALYSIS")
    print("=" * 70)
    
    stats = df.groupby('scenario').agg({
        'payload_size_before_bytes': ['mean', 'min', 'max'],
        'payload_size_bytes': ['mean', 'min', 'max'],
        'serialization_overhead_bytes': ['mean', 'std', 'min', 'max'],
        'serialization_overhead_percent': ['mean', 'std', 'min', 'max'],
        'compression_ratio': ['mean', 'std']
    }).round(2)
    
    print("\n📈 Serialization Statistics by Scenario:")
    print(stats)
    
    # Detailed breakdown by category
    category_stats = df.groupby(['scenario', 'payload_category']).agg({
        'payload_size_before_bytes': 'mean',
        'payload_size_bytes': 'mean',
        'serialization_overhead_bytes': 'mean',
        'serialization_overhead_percent': 'mean',
        'compression_ratio': 'mean'
    }).round(2)
    
    print("\n📊 Overhead by Scenario and Payload Category:")
    print(category_stats)
    
    # Compare protocols
    print("\n🔍 Protocol Comparison:")
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario]
        avg_overhead_pct = scenario_df['serialization_overhead_percent'].mean()
        avg_overhead_bytes = scenario_df['serialization_overhead_bytes'].mean()
        avg_compression = scenario_df['compression_ratio'].mean()
        
        print(f"   {scenario}:")
        print(f"      Avg overhead: {avg_overhead_bytes:.2f} bytes ({avg_overhead_pct:.2f}%)")
        print(f"      Compression ratio: {avg_compression:.3f}x")
        
        if avg_overhead_bytes < 0:
            print(f"      ✨ Achieves {abs(avg_overhead_bytes):.2f} bytes compression on average")
        else:
            print(f"      ⚠️  Adds {avg_overhead_bytes:.2f} bytes overhead on average")
    
    return stats, category_stats

def compare_protocols(df):
    """Compare serialization efficiency between protocols"""
    print("\n" + "=" * 70)
    print("  MQTT vs gRPC SERIALIZATION COMPARISON")
    print("=" * 70)
    
    mqtt_df = df[df['protocol'] == 'mqtt']
    grpc_df = df[df['protocol'] == 'grpc']
    
    if len(mqtt_df) > 0 and len(grpc_df) > 0:
        mqtt_overhead = mqtt_df['serialization_overhead_percent'].mean()
        grpc_overhead = grpc_df['serialization_overhead_percent'].mean()
        
        print(f"\n📊 Average Serialization Overhead:")
        print(f"   MQTT (JSON): {mqtt_overhead:.2f}%")
        print(f"   gRPC (Protobuf): {grpc_overhead:.2f}%")
        
        if grpc_overhead < mqtt_overhead:
            improvement = mqtt_overhead - grpc_overhead
            print(f"\n✅ gRPC is {improvement:.2f}% more efficient than MQTT")
        else:
            difference = grpc_overhead - mqtt_overhead
            print(f"\n⚠️  MQTT is {difference:.2f}% more efficient than gRPC")
    else:
        print("⚠️  Need data from both MQTT and gRPC to compare")

# ==========================================================
# VISUALIZATION - UNIFIED DASHBOARD
# ==========================================================

def create_unified_dashboard(df, output_dir):
    """Create a unified dashboard with all key visualizations"""
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # ========== SUBPLOT 1: Latency by Payload Category ==========
    ax1 = fig.add_subplot(gs[0, :2])
    
    avg_latency = df.groupby(['scenario', 'payload_category'])['latency_ms'].mean().reset_index()
    
    sns.barplot(
        data=avg_latency,
        x='payload_category',
        y='latency_ms',
        hue='scenario',
        ax=ax1
    )
    
    ax1.set_xlabel('Payload Size Category', fontsize=10)
    ax1.set_ylabel('Average Latency (ms)', fontsize=10)
    ax1.set_title('Latency Comparison by Payload Size', fontsize=12, fontweight='bold')
    ax1.legend(title='Protocol', fontsize=8, title_fontsize=9, loc='upper left')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # ========== SUBPLOT 2: Serialization Overhead by Scenario ==========
    ax2 = fig.add_subplot(gs[0, 2])
    
    avg_overhead = df.groupby('scenario')['serialization_overhead_bytes'].mean().sort_values()
    colors = ['green' if x < 0 else 'red' for x in avg_overhead.values]
    
    avg_overhead.plot(kind='barh', color=colors, ax=ax2)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax2.set_xlabel('Avg Overhead (bytes)', fontsize=10)
    ax2.set_title('Serialization Overhead', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')
    
    # ========== SUBPLOT 3: Overhead by Payload Category ==========
    ax3 = fig.add_subplot(gs[1, :2])
    
    overhead_by_cat = df.groupby(['scenario', 'payload_category'])['serialization_overhead_bytes'].mean().reset_index()
    
    sns.barplot(
        data=overhead_by_cat,
        x='payload_category',
        y='serialization_overhead_bytes',
        hue='scenario',
        ax=ax3
    )
    
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax3.set_xlabel('Payload Size Category', fontsize=10)
    ax3.set_ylabel('Avg Overhead (bytes)', fontsize=10)
    ax3.set_title('Serialization Overhead by Payload Size', fontsize=12, fontweight='bold')
    ax3.legend(title='Protocol', fontsize=8, title_fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # ========== SUBPLOT 4: Compression Ratio ==========
    ax4 = fig.add_subplot(gs[1, 2])
    
    avg_compression = df.groupby('scenario')['compression_ratio'].mean().sort_values()
    avg_compression.plot(kind='barh', color='steelblue', ax=ax4)
    ax4.axvline(x=1.0, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax4.set_xlabel('Compression Ratio', fontsize=10)
    ax4.set_title('Compression Efficiency\n(>1.0 = compression)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')
    
    # ========== SUBPLOT 5: Latency vs Payload Size (Scatter) ==========
    ax5 = fig.add_subplot(gs[2, :2])
    
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario]
        ax5.scatter(
            scenario_df['payload_size_before_bytes'],
            scenario_df['latency_ms'],
            alpha=0.4,
            s=10,
            label=scenario
        )
    
    ax5.set_xlabel('Payload Size Before Serialization (bytes)', fontsize=10)
    ax5.set_ylabel('Latency (ms)', fontsize=10)
    ax5.set_title('Latency vs Payload Size', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=8, loc='upper left')
    ax5.grid(True, alpha=0.3)
    
    # ========== SUBPLOT 6: Before vs After Size ==========
    ax6 = fig.add_subplot(gs[2, 2])
    
    for scenario in df['scenario'].unique():
        scenario_df = df[df['scenario'] == scenario]
        ax6.scatter(
            scenario_df['payload_size_before_bytes'],
            scenario_df['payload_size_bytes'],
            alpha=0.4,
            s=10,
            label=scenario
        )
    
    # Diagonal line
    max_size = max(df['payload_size_before_bytes'].max(), df['payload_size_bytes'].max())
    ax6.plot([0, max_size], [0, max_size], 'k--', alpha=0.5, linewidth=1)
    
    ax6.set_xlabel('Before (bytes)', fontsize=10)
    ax6.set_ylabel('After (bytes)', fontsize=10)
    ax6.set_title('Payload: Before vs After', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=7, loc='upper left')
    ax6.grid(True, alpha=0.3)
    
    # Main title
    fig.suptitle('Protocol Performance Analysis: MQTT vs gRPC Serialization & Latency', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Save
    filepath = os.path.join(output_dir, 'unified_analysis_dashboard.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"✅ Saved unified dashboard: {filepath}")
    plt.close()

# ==========================================================
# EXPORT RESULTS
# ==========================================================

def export_statistics(df, output_dir):
    """Export serialization statistics to CSV"""
    # Summary by scenario
    summary = df.groupby('scenario').agg({
        'payload_size_before_bytes': ['count', 'mean', 'std', 'min', 'max'],
        'payload_size_bytes': ['mean', 'std', 'min', 'max'],
        'serialization_overhead_bytes': ['mean', 'std', 'min', 'max'],
        'serialization_overhead_percent': ['mean', 'std', 'min', 'max'],
        'compression_ratio': ['mean', 'std'],
        'latency_ms': ['mean', 'std']
    }).round(2)
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    
    filepath = os.path.join(output_dir, 'serialization_summary.csv')
    summary.to_csv(filepath)
    print(f"✅ Saved: {filepath}")
    
    # Detailed data by category
    category_summary = df.groupby(['scenario', 'payload_category']).agg({
        'payload_size_before_bytes': ['count', 'mean'],
        'payload_size_bytes': 'mean',
        'serialization_overhead_bytes': 'mean',
        'serialization_overhead_percent': 'mean',
        'compression_ratio': 'mean',
        'latency_ms': 'mean'
    }).round(2)
    category_summary.columns = ['_'.join(col).strip() for col in category_summary.columns.values]
    
    filepath = os.path.join(output_dir, 'serialization_by_category.csv')
    category_summary.to_csv(filepath)
    print(f"✅ Saved: {filepath}")
    
    # Detailed records export
    export_cols = [
        'scenario', 'protocol', 'use_tls', 
        'payload_size_before_bytes', 'payload_size_bytes',
        'serialization_overhead_bytes', 'serialization_overhead_percent',
        'compression_ratio', 'latency_ms', 'created_at'
    ]
    detailed_filepath = os.path.join(output_dir, 'serialization_detailed.csv')
    df[export_cols].to_csv(detailed_filepath, index=False)
    print(f"✅ Saved: {detailed_filepath}")

# ==========================================================
# MAIN
# ==========================================================

def main():
    print("=" * 70)
    print("  PAYLOAD SERIALIZATION ANALYSIS v2")
    print("  Analyzing overhead: Payload Before vs After Serialization")
    print("=" * 70)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'results', 'serialization_analysis')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📂 Output directory: {output_dir}")
    
    # Connect to database
    conn = connect_db()
    
    # Load data
    df = load_data(conn)
    
    if len(df) == 0:
        print("\n⚠️  No data found for analysis.")
        print("   Run: ./run_experiments_with_payload.sh")
        conn.close()
        return
    
    # Prepare data
    df = prepare_data(df)
    
    # Statistical analysis
    stats, category_stats = compute_serialization_stats(df)
    compare_protocols(df)
    
    # Generate unified dashboard
    print("\n📊 Generating unified dashboard...")
    create_unified_dashboard(df, output_dir)
    
    # Export results
    print("\n💾 Exporting statistics...")
    export_statistics(df, output_dir)
    
    # Close connection
    conn.close()
    
    print("\n" + "=" * 70)
    print("  ✅ SERIALIZATION ANALYSIS COMPLETE!")
    print(f"     Dashboard saved to: {output_dir}/unified_analysis_dashboard.png")
    print(f"     CSV files saved to: {output_dir}/")
    print("=" * 70)
    print("\n💡 Key Insights:")
    print("   - Negative overhead = Protocol achieves compression")
    print("   - Positive overhead = Protocol adds extra bytes")
    print("   - Compression ratio >1.0 = Efficient serialization")
    print("   - Dashboard shows latency comparison by payload size")
    print("=" * 70)

if __name__ == "__main__":
    main()
