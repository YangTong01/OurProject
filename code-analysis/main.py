#!/usr/bin/env python3
"""
Flask代码演化分析主程序
分析代码结构变化、文件类型演化、测试覆盖等
"""

import argparse
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime

from src.git_analyzer import GitRepositoryAnalyzer
from src.code_analyzer import CodeStructureAnalyzer
from src.test_analyzer import TestCoverageAnalyzer
from src.visualization import VisualizationEngine

def load_config(config_path="config.yaml"):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def clone_flask_repo(config):
    """克隆Flask仓库（如果尚未克隆）"""
    from git import Repo
    import os
    
    clone_path = Path(config['project']['clone_path'])
    
    if not clone_path.exists():
        print(f"Cloning Flask repository to {clone_path}...")
        Repo.clone_from(
            config['project']['flask_repo_url'],
            clone_path
        )
        print("Clone completed.")
    else:
        print(f"Repository already exists at {clone_path}")

def analyze_code_evolution(config):
    """执行代码演化分析"""
    print("=" * 60)
    print("Flask Code Evolution Analysis")
    print("=" * 60)
    
    # 1. 初始化分析器
    git_analyzer = GitRepositoryAnalyzer(config)
    code_analyzer = CodeStructureAnalyzer(config)
    test_analyzer = TestCoverageAnalyzer(config)
    visualizer = VisualizationEngine(config)
    
    # 2. 分析Git历史
    print("\n[Phase 1] Analyzing Git commit history...")
    commit_data = git_analyzer.extract_commit_history()
    
    # 3. 分析代码结构变化
    print("\n[Phase 2] Analyzing code structure evolution...")
    structure_metrics = code_analyzer.analyze_structure_evolution(commit_data)
    
    # 4. 分析文件类型演化
    print("\n[Phase 3] Analyzing file type evolution...")
    filetype_evolution = code_analyzer.analyze_filetype_evolution(commit_data)
    
    # 5. 分析测试覆盖率
    print("\n[Phase 4] Analyzing test coverage evolution...")
    test_metrics = test_analyzer.analyze_test_coverage(commit_data)
    
    # 6. 生成可视化图表
    print("\n[Phase 5] Generating visualizations...")
    visualizer.generate_all_visualizations(
        commit_data, 
        structure_metrics,
        filetype_evolution,
        test_metrics
    )
    
    # 7. 保存结果
    print("\n[Phase 6] Saving results...")
    save_results(commit_data, structure_metrics, filetype_evolution, test_metrics)
    
    print("\n" + "=" * 60)
    print("Analysis completed successfully!")
    print("=" * 60)

def save_results(commit_data, structure_metrics, filetype_evolution, test_metrics):
    """保存分析结果"""
    data_dir = Path("data/processed")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存为CSV文件
    commit_data.to_csv(data_dir / "commit_history.csv", index=False, encoding='utf-8')
    structure_metrics.to_csv(data_dir / "code_structure_evolution.csv", index=False, encoding='utf-8')
    
    if not filetype_evolution.empty:
        filetype_evolution.to_csv(data_dir / "filetype_evolution.csv", index=False, encoding='utf-8')
    
    if not test_metrics.empty:
        test_metrics.to_csv(data_dir / "test_coverage_evolution.csv", index=False, encoding='utf-8')
    
    # 生成汇总报告
    generate_summary_report(commit_data, structure_metrics, test_metrics)

def generate_summary_report(commit_data, structure_metrics, test_metrics):
    """生成分析摘要报告"""
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    
    summary = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_commits": len(commit_data),
        "time_period": f"{commit_data['date'].min()} to {commit_data['date'].max()}",
        "unique_authors": commit_data['author'].nunique(),
        "avg_commit_size": commit_data['files_changed'].mean(),
        "avg_lines_changed": commit_data['lines_changed'].mean(),
        "test_coverage_trend": "N/A"
    }
    
    # 添加结构指标
    if not structure_metrics.empty:
        summary['total_files_latest'] = structure_metrics['total_files'].iloc[-1]
        summary['total_lines_latest'] = structure_metrics['total_lines'].iloc[-1]
        summary['source_files_latest'] = structure_metrics['source_files'].iloc[-1]
        summary['test_files_latest'] = structure_metrics['test_files'].iloc[-1]
    
    # 添加提交类型分布
    if 'commit_type' in commit_data.columns:
        type_counts = commit_data['commit_type'].value_counts()
        for type_name, count in type_counts.items():
            percentage = count / len(commit_data) * 100
            summary[f'{type_name}_commits'] = f"{count} ({percentage:.1f}%)"
    
    # 添加测试覆盖率趋势
    if not test_metrics.empty:
        # 检查列名
        if 'test_ratio_files' in test_metrics.columns:
            test_ratio_col = 'test_ratio_files'
        elif 'test_ratio_lines' in test_metrics.columns:
            test_ratio_col = 'test_ratio_lines'
        else:
            test_ratio_col = None
        
        if test_ratio_col and len(test_metrics) > 1:
            first_value = test_metrics[test_ratio_col].iloc[0]
            last_value = test_metrics[test_ratio_col].iloc[-1]
            
            if not (pd.isna(first_value) or pd.isna(last_value)):
                if last_value > first_value:
                    summary['test_coverage_trend'] = "Increasing"
                else:
                    summary['test_coverage_trend'] = "Decreasing"
                
                summary['test_coverage_current'] = f"{last_value:.2%}"
    
    with open(report_dir / "analysis_summary.txt", "w", encoding='utf-8') as f:
        f.write("Flask Code Evolution Analysis Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Analysis Date: {summary['analysis_date']}\n")
        f.write(f"Total Commits: {summary['total_commits']}\n")
        f.write(f"Time Period: {summary['time_period']}\n")
        f.write(f"Unique Authors: {summary['unique_authors']}\n")
        f.write(f"Average Commit Size: {summary['avg_commit_size']:.2f} files\n")
        f.write(f"Average Lines Changed per Commit: {summary['avg_lines_changed']:.2f} lines\n")
        
        if 'total_files_latest' in summary:
            f.write(f"\nLatest Code Statistics:\n")
            f.write(f"  Total Files: {summary['total_files_latest']}\n")
            f.write(f"  Total Lines: {summary['total_lines_latest']}\n")
            f.write(f"  Source Files: {summary['source_files_latest']}\n")
            f.write(f"  Test Files: {summary['test_files_latest']}\n")
        
        f.write(f"\nTest Coverage Trend: {summary['test_coverage_trend']}\n")
        if 'test_coverage_current' in summary:
            f.write(f"Current Test Coverage: {summary['test_coverage_current']}\n")
        
        # 提交类型分布详细信息
        if 'commit_type' in commit_data.columns:
            f.write("\nCommit Type Distribution:\n")
            type_counts = commit_data['commit_type'].value_counts()
            total = len(commit_data)
            for type_name, count in type_counts.items():
                percentage = count / total * 100
                f.write(f"  {type_name}: {count} ({percentage:.1f}%)\n")
        
        # 主要贡献者
        if 'author' in commit_data.columns:
            f.write("\nTop 10 Contributors:\n")
            top_authors = commit_data['author'].value_counts().head(10)
            for i, (author, count) in enumerate(top_authors.items(), 1):
                percentage = count / len(commit_data) * 100
                f.write(f"  {i:2d}. {author[:40]:40s} {count:4d} ({percentage:.1f}%)\n")

def main():
    parser = argparse.ArgumentParser(description="Flask代码演化分析工具")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--clone-only", action="store_true", help="仅克隆仓库，不进行分析")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if args.clone_only:
        clone_flask_repo(config)
    else:
        clone_flask_repo(config)
        analyze_code_evolution(config)

if __name__ == "__main__":
    main()