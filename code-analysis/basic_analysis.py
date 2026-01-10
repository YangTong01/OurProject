# basic_analysis.py
#!/usr/bin/env python3
"""
基础分析 - 只做Git历史分析
"""

import argparse
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

def load_config(config_path="config.yaml"):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def run_basic_analysis(config):
    """运行基础分析"""
    print("=" * 60)
    print("Flask基础代码演化分析")
    print("=" * 60)
    
    # 导入修复后的分析器
    from src.git_analyzer import GitRepositoryAnalyzer
    
    # 1. 分析Git历史
    print("\n[阶段1] 分析Git提交历史...")
    analyzer = GitRepositoryAnalyzer(config)
    commit_data = analyzer.extract_commit_history()
    
    if commit_data.empty:
        print("没有获取到提交数据，无法继续分析")
        return
    
    # 2. 保存数据
    data_dir = Path("data/basic")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    commit_data.to_csv(data_dir / "basic_commit_history.csv", index=False, encoding='utf-8')
    print(f"数据已保存到 {data_dir / 'basic_commit_history.csv'}")
    
    # 3. 生成基础图表
    figures_dir = Path("figures/basic")
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置样式
    plt.style.use('seaborn-v0_8')
    
    # 图表1: 提交频率
    plt.figure(figsize=(12, 6))
    monthly_commits = commit_data.set_index('date').resample('M').size()
    plt.plot(monthly_commits.index, monthly_commits.values, linewidth=2)
    plt.title('Monthly Commit Activity', fontsize=16, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Number of Commits')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / 'commit_activity.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 图表2: 提交类型分布
    plt.figure(figsize=(10, 8))
    type_counts = commit_data['commit_type'].value_counts()
    plt.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%', startangle=90)
    plt.title('Commit Type Distribution', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(figures_dir / 'commit_types.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 图表3: 作者贡献
    if 'author' in commit_data.columns:
        author_stats = analyzer.analyze_authors_contribution(commit_data)
        if not author_stats.empty:
            plt.figure(figsize=(12, 8))
            top_authors = author_stats.head(15)
            plt.barh(range(len(top_authors)), top_authors['commit_count'].values)
            plt.yticks(range(len(top_authors)), top_authors.index)
            plt.xlabel('Number of Commits')
            plt.title('Top 15 Contributors', fontsize=16, fontweight='bold')
            plt.tight_layout()
            plt.savefig(figures_dir / 'top_contributors.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    # 4. 生成报告
    report_dir = Path("reports/basic")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    with open(report_dir / "basic_analysis_report.txt", "w", encoding='utf-8') as f:
        f.write("Flask Basic Code Evolution Analysis Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Commits: {len(commit_data)}\n")
        f.write(f"Time Period: {commit_data['date'].min().strftime('%Y-%m-%d')} to {commit_data['date'].max().strftime('%Y-%m-%d')}\n")
        f.write(f"Unique Authors: {commit_data['author'].nunique()}\n")
        f.write(f"Average Files Changed per Commit: {commit_data['files_changed'].mean():.2f}\n")
        f.write(f"Average Lines Changed per Commit: {commit_data['lines_changed'].mean():.2f}\n\n")
        
        # 提交类型统计
        f.write("Commit Type Distribution:\n")
        type_counts = commit_data['commit_type'].value_counts()
        for type_name, count in type_counts.items():
            percentage = count / len(commit_data) * 100
            f.write(f"  {type_name}: {count} ({percentage:.1f}%)\n")
    
    print(f"\n报告已保存到 {report_dir / 'basic_analysis_report.txt'}")
    print(f"图表已保存到 {figures_dir}/")
    
    print("\n" + "=" * 60)
    print("基础分析完成！")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="基础Flask代码分析")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    run_basic_analysis(config)

if __name__ == "__main__":
    main()