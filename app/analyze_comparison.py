"""
Protocol Comparison Analysis

This script compares MQTT vs gRPC protocols analyzing:
- Average latency and P95 latency
- Impact of TLS on both protocols
- Performance across different payload sizes

Usage:
    python analyze_comparison.py
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import psycopg2
from matplotlib.gridspec import GridSpec

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (20, 12)
plt.rcParams['font.size'] = 10

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
        print("\nMake sure PostgreSQL container is running:")
        print("  docker compose up postgres -d")
        sys.exit(1)

# ==========================================================
# DATA LOADING & PREPARATION
# ==========================================================

def load_and_prepare_data(conn):
    """Load and prepare data for analysis"""
    query = """
        SELECT 
            protocol,
            use_tls,
            latency_ms,
            payload_size_bytes,
            created_at
        FROM message_logs
        ORDER BY created_at
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        print(f"✅ Loaded {len(df):,} records")
        
        if len(df) == 0:
            print("⚠️  No data found in database. Run experiments first.")
            return None
        
        # Create scenario labels
        df['scenario'] = df.apply(
            lambda row: f"{row['protocol'].upper()}_{'TLS' if row['use_tls'] else 'Plain'}", 
            axis=1
        )
        
        df['tls_label'] = df['use_tls'].map({True: 'TLS', False: 'Plain'})
        df['protocol_upper'] = df['protocol'].str.upper()
        
        # Create payload size categories
        df['payload_category'] = pd.cut(
            df['payload_size_bytes'],
            bins=[0, 500, 1000, 2000, 5000, float('inf')],
            labels=['<500B', '500B-1KB', '1KB-2KB', '2KB-5KB', '>5KB']
        )
        
        print(f"\n📊 Data Summary:")
        print(f"   Protocols: {df['protocol'].unique()}")
        print(f"   Scenarios: {df['scenario'].unique()}")
        print(f"   Records per scenario:")
        for scenario, count in df['scenario'].value_counts().items():
            print(f"      {scenario}: {count:,}")
        
        return df
        
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        sys.exit(1)

# ==========================================================
# STATISTICAL COMPUTATIONS
# ==========================================================

def compute_statistics(df):
    """Compute mean and P95 latency statistics"""
    stats = df.groupby(['protocol_upper', 'tls_label', 'payload_category'])['latency_ms'].agg([
        ('mean', 'mean'),
        ('p95', lambda x: np.percentile(x, 95)),
        ('p50', 'median'),
        ('std', 'std'),
        ('count', 'count')
    ]).reset_index()
    
    return stats

# ==========================================================
# VISUALIZATION - COMPREHENSIVE COMPARISON
# ==========================================================

def create_comparison_dashboard(df, stats, output_dir):
    """Create comprehensive comparison dashboard with multiple charts"""
    
    # Create figure with custom grid
    fig = plt.figure(figsize=(20, 14))
    gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Color palette
    protocol_colors = {'MQTT': '#2E86AB', 'GRPC': '#A23B72'}
    tls_colors = {'Plain': '#06A77D', 'TLS': '#D62246'}
    
    # ============================================================
    # 1. Average Latency: MQTT vs gRPC by Payload Size
    # ============================================================
    ax1 = fig.add_subplot(gs[0, 0])
    mqtt_mean = stats[stats['protocol_upper'] == 'MQTT'].groupby('payload_category')['mean'].mean()
    grpc_mean = stats[stats['protocol_upper'] == 'GRPC'].groupby('payload_category')['mean'].mean()
    
    x = np.arange(len(mqtt_mean))
    width = 0.35
    
    ax1.bar(x - width/2, mqtt_mean.values, width, label='MQTT', color=protocol_colors['MQTT'], alpha=0.8)
    ax1.bar(x + width/2, grpc_mean.values, width, label='gRPC', color=protocol_colors['GRPC'], alpha=0.8)
    
    ax1.set_xlabel('Payload Size Category', fontweight='bold')
    ax1.set_ylabel('Average Latency (ms)', fontweight='bold')
    ax1.set_title('Average Latency: MQTT vs gRPC', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(mqtt_mean.index, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # ============================================================
    # 2. P95 Latency: MQTT vs gRPC by Payload Size
    # ============================================================
    ax2 = fig.add_subplot(gs[0, 1])
    mqtt_p95 = stats[stats['protocol_upper'] == 'MQTT'].groupby('payload_category')['p95'].mean()
    grpc_p95 = stats[stats['protocol_upper'] == 'GRPC'].groupby('payload_category')['p95'].mean()
    
    ax2.bar(x - width/2, mqtt_p95.values, width, label='MQTT', color=protocol_colors['MQTT'], alpha=0.8)
    ax2.bar(x + width/2, grpc_p95.values, width, label='gRPC', color=protocol_colors['GRPC'], alpha=0.8)
    
    ax2.set_xlabel('Payload Size Category', fontweight='bold')
    ax2.set_ylabel('P95 Latency (ms)', fontweight='bold')
    ax2.set_title('P95 Latency: MQTT vs gRPC', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(mqtt_p95.index, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # ============================================================
    # 3. TLS Impact on MQTT
    # ============================================================
    ax3 = fig.add_subplot(gs[0, 2])
    mqtt_data = stats[stats['protocol_upper'] == 'MQTT']
    
    mqtt_plain = mqtt_data[mqtt_data['tls_label'] == 'Plain'].groupby('payload_category')['mean'].mean()
    mqtt_tls = mqtt_data[mqtt_data['tls_label'] == 'TLS'].groupby('payload_category')['mean'].mean()
    
    ax3.plot(mqtt_plain.index, mqtt_plain.values, marker='o', linewidth=2, label='Plain', color=tls_colors['Plain'])
    ax3.plot(mqtt_tls.index, mqtt_tls.values, marker='s', linewidth=2, label='TLS', color=tls_colors['TLS'])
    
    ax3.set_xlabel('Payload Size Category', fontweight='bold')
    ax3.set_ylabel('Average Latency (ms)', fontweight='bold')
    ax3.set_title('MQTT: TLS vs Plain', fontsize=12, fontweight='bold')
    ax3.tick_params(axis='x', rotation=45)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # ============================================================
    # 4. TLS Impact on gRPC
    # ============================================================
    ax4 = fig.add_subplot(gs[1, 0])
    grpc_data = stats[stats['protocol_upper'] == 'GRPC']
    
    grpc_plain = grpc_data[grpc_data['tls_label'] == 'Plain'].groupby('payload_category')['mean'].mean()
    grpc_tls = grpc_data[grpc_data['tls_label'] == 'TLS'].groupby('payload_category')['mean'].mean()
    
    ax4.plot(grpc_plain.index, grpc_plain.values, marker='o', linewidth=2, label='Plain', color=tls_colors['Plain'])
    ax4.plot(grpc_tls.index, grpc_tls.values, marker='s', linewidth=2, label='TLS', color=tls_colors['TLS'])
    
    ax4.set_xlabel('Payload Size Category', fontweight='bold')
    ax4.set_ylabel('Average Latency (ms)', fontweight='bold')
    ax4.set_title('gRPC: TLS vs Plain', fontsize=12, fontweight='bold')
    ax4.tick_params(axis='x', rotation=45)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # ============================================================
    # 5. Box Plot: Overall Comparison
    # ============================================================
    ax5 = fig.add_subplot(gs[1, 1])
    
    # Prepare data for boxplot
    box_data = []
    box_labels = []
    positions = []
    colors_list = []
    
    pos = 0
    for protocol in ['MQTT', 'GRPC']:
        for tls in ['Plain', 'TLS']:
            data = df[(df['protocol_upper'] == protocol) & (df['tls_label'] == tls)]['latency_ms']
            if len(data) > 0:
                box_data.append(data)
                box_labels.append(f"{protocol}\n{tls}")
                positions.append(pos)
                colors_list.append(protocol_colors[protocol] if tls == 'Plain' else protocol_colors[protocol])
                pos += 1
        pos += 0.5  # Gap between protocols
    
    bp = ax5.boxplot(box_data, positions=positions, widths=0.6, patch_artist=True,
                     showfliers=False, medianprops=dict(color='red', linewidth=2))
    
    for patch, color in zip(bp['boxes'], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    ax5.set_xticks(positions)
    ax5.set_xticklabels(box_labels, fontsize=9)
    ax5.set_ylabel('Latency (ms)', fontweight='bold')
    ax5.set_title('Latency Distribution Comparison', fontsize=12, fontweight='bold')
    ax5.grid(axis='y', alpha=0.3)
    
    # ============================================================
    # 6. Heatmap: Mean Latency
    # ============================================================
    ax6 = fig.add_subplot(gs[1, 2])
    
    pivot_mean = df.pivot_table(
        values='latency_ms',
        index='payload_category',
        columns='scenario',
        aggfunc='mean'
    )
    
    sns.heatmap(pivot_mean, annot=True, fmt='.2f', cmap='YlOrRd', ax=ax6, cbar_kws={'label': 'Latency (ms)'})
    ax6.set_title('Mean Latency Heatmap', fontsize=12, fontweight='bold')
    ax6.set_xlabel('Scenario', fontweight='bold')
    ax6.set_ylabel('Payload Size', fontweight='bold')
    
    # ============================================================
    # 7. Mean vs P95 Comparison
    # ============================================================
    ax7 = fig.add_subplot(gs[2, 0])
    
    scenario_stats = df.groupby('scenario')['latency_ms'].agg([
        ('mean', 'mean'),
        ('p95', lambda x: np.percentile(x, 95))
    ]).reset_index()
    
    x_pos = np.arange(len(scenario_stats))
    width = 0.35
    
    ax7.bar(x_pos - width/2, scenario_stats['mean'], width, label='Mean', alpha=0.8)
    ax7.bar(x_pos + width/2, scenario_stats['p95'], width, label='P95', alpha=0.8)
    
    ax7.set_xlabel('Scenario', fontweight='bold')
    ax7.set_ylabel('Latency (ms)', fontweight='bold')
    ax7.set_title('Mean vs P95 Latency by Scenario', fontsize=12, fontweight='bold')
    ax7.set_xticks(x_pos)
    ax7.set_xticklabels(scenario_stats['scenario'], rotation=45, ha='right')
    ax7.legend()
    ax7.grid(axis='y', alpha=0.3)
    
    # ============================================================
    # 8. Protocol Efficiency: Latency per Byte
    # ============================================================
    ax8 = fig.add_subplot(gs[2, 1])
    
    df['latency_per_byte'] = df['latency_ms'] / df['payload_size_bytes']
    efficiency = df.groupby(['protocol_upper', 'tls_label'])['latency_per_byte'].mean().reset_index()
    
    x_pos = np.arange(len(efficiency))
    colors_eff = [protocol_colors[row['protocol_upper']] for _, row in efficiency.iterrows()]
    
    bars = ax8.bar(x_pos, efficiency['latency_per_byte'], color=colors_eff, alpha=0.7)
    
    # Add pattern for TLS
    for i, (_, row) in enumerate(efficiency.iterrows()):
        if row['tls_label'] == 'TLS':
            bars[i].set_hatch('//')
    
    ax8.set_xlabel('Protocol Configuration', fontweight='bold')
    ax8.set_ylabel('Latency per Byte (ms/byte)', fontweight='bold')
    ax8.set_title('Protocol Efficiency', fontsize=12, fontweight='bold')
    ax8.set_xticks(x_pos)
    ax8.set_xticklabels([f"{row['protocol_upper']}\n{row['tls_label']}" for _, row in efficiency.iterrows()], fontsize=9)
    ax8.grid(axis='y', alpha=0.3)
    
    # ============================================================
    # 9. Summary Statistics Table
    # ============================================================
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('tight')
    ax9.axis('off')
    
    # Prepare summary table
    summary_data = df.groupby('scenario')['latency_ms'].agg([
        ('Mean', lambda x: f"{x.mean():.2f}"),
        ('P95', lambda x: f"{np.percentile(x, 95):.2f}"),
        ('P50', lambda x: f"{x.median():.2f}"),
        ('Std', lambda x: f"{x.std():.2f}"),
        ('Count', 'count')
    ]).reset_index()
    
    table = ax9.table(cellText=summary_data.values, colLabels=summary_data.columns,
                      cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Style header
    for i in range(len(summary_data.columns)):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(summary_data) + 1):
        for j in range(len(summary_data.columns)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#F2F2F2')
    
    ax9.set_title('Summary Statistics (ms)', fontsize=12, fontweight='bold', pad=20)
    
    # Overall title
    fig.suptitle('IoT Protocol Performance Comparison: MQTT vs gRPC', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Save figure
    filepath = os.path.join(output_dir, 'protocol_comparison_dashboard.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"\n✅ Saved comprehensive dashboard: {filepath}")
    plt.close()

# ==========================================================
# EXPORT STATISTICS
# ==========================================================

def export_comparison_stats(df, stats, output_dir):
    """Export comparison statistics to CSV"""
    
    # Detailed statistics
    filepath = os.path.join(output_dir, 'comparison_statistics.csv')
    stats.to_csv(filepath, index=False)
    print(f"✅ Saved: {filepath}")
    
    # Protocol summary
    protocol_summary = df.groupby(['protocol_upper', 'tls_label'])['latency_ms'].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('p50', 'median'),
        ('p95', lambda x: np.percentile(x, 95)),
        ('p99', lambda x: np.percentile(x, 99)),
        ('std', 'std'),
        ('min', 'min'),
        ('max', 'max')
    ]).round(2)
    
    filepath = os.path.join(output_dir, 'protocol_summary.csv')
    protocol_summary.to_csv(filepath)
    print(f"✅ Saved: {filepath}")
    
    # Display summary
    print("\n" + "=" * 80)
    print("PROTOCOL COMPARISON SUMMARY")
    print("=" * 80)
    print(protocol_summary)
    print("=" * 80)

# ==========================================================
# MAIN
# ==========================================================

def main():
    print("=" * 80)
    print("  PROTOCOL COMPARISON ANALYSIS: MQTT vs gRPC")
    print("=" * 80)
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'results', 'comparison_analysis')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📂 Output directory: {output_dir}")
    
    # Connect to database
    conn = connect_db()
    
    # Load and prepare data
    df = load_and_prepare_data(conn)
    
    if df is None:
        conn.close()
        return
    
    # Compute statistics
    print("\n📊 Computing statistics...")
    stats = compute_statistics(df)
    
    # Create comprehensive dashboard
    print("\n🎨 Creating comparison dashboard...")
    create_comparison_dashboard(df, stats, output_dir)
    
    # Export statistics
    print("\n💾 Exporting statistics...")
    export_comparison_stats(df, stats, output_dir)
    
    # Close connection
    conn.close()
    
    print("\n" + "=" * 80)
    print("  ✅ COMPARISON ANALYSIS COMPLETE!")
    print(f"     Results saved to: {output_dir}")
    print("=" * 80)

if __name__ == "__main__":
    main()
