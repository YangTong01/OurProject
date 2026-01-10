"""
数据可视化模块
"""

import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib

# 设置中文字体（如果需要）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

class VisualizationEngine:
    def __init__(self, config):
        self.config = config
        self.figures_dir = Path("figures")
        self.figures_dir.mkdir(exist_ok=True)
        
        # 设置样式
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        
    def generate_all_visualizations(self, commit_data, structure_metrics, 
                                  filetype_evolution, test_metrics):
        """生成所有可视化图表"""
        
        # 1. 提交活动趋势
        self.plot_commit_activity(commit_data)
        
        # 2. 代码规模增长
        self.plot_code_growth(structure_metrics)
        
        # 3. 文件类型演化
        if not filetype_evolution.empty:
            self.plot_filetype_evolution(filetype_evolution)
        
        # 4. 测试覆盖率趋势（如果有数据）
        if not test_metrics.empty:
            self.plot_test_coverage_trend(test_metrics)
        
        # 5. 代码结构变化
        self.plot_structure_changes(structure_metrics)
        
        # 6. 作者贡献热力图
        self.plot_author_heatmap(commit_data)
        
        print(f"所有可视化图表保存到 {self.figures_dir}")
    
    def plot_commit_activity(self, commit_data):
        """绘制提交活动趋势"""
        if commit_data.empty:
            print("警告: 提交数据为空，无法绘制活动趋势")
            return
            
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        try:
            # 按月统计提交
            monthly_commits = commit_data.set_index('date').resample('M').size()
            
            axes[0, 0].plot(monthly_commits.index, monthly_commits.values, linewidth=2)
            axes[0, 0].set_title('Monthly Commit Activity', fontsize=14, fontweight='bold')
            axes[0, 0].set_xlabel('Date')
            axes[0, 0].set_ylabel('Number of Commits')
            axes[0, 0].grid(True, alpha=0.3)
            
            # 按年统计
            if 'year' in commit_data.columns:
                yearly_commits = commit_data.groupby('year').size()
                axes[0, 1].bar(yearly_commits.index, yearly_commits.values, alpha=0.7)
                axes[0, 1].set_title('Yearly Commit Count', fontsize=14, fontweight='bold')
                axes[0, 1].set_xlabel('Year')
                axes[0, 1].set_ylabel('Number of Commits')
            
            # 提交类型分布
            if 'commit_type' in commit_data.columns:
                commit_types = commit_data['commit_type'].value_counts()
                axes[1, 0].pie(commit_types.values, labels=commit_types.index, autopct='%1.1f%%')
                axes[1, 0].set_title('Commit Type Distribution', fontsize=14, fontweight='bold')
            
            # 提交大小分布
            if 'lines_changed' in commit_data.columns:
                axes[1, 1].hist(commit_data['lines_changed'], bins=50, alpha=0.7, edgecolor='black')
                axes[1, 1].set_title('Distribution of Commit Sizes', fontsize=14, fontweight='bold')
                axes[1, 1].set_xlabel('Lines Changed per Commit')
                axes[1, 1].set_ylabel('Frequency')
                axes[1, 1].set_yscale('log')
            
            plt.tight_layout()
            plt.savefig(self.figures_dir / 'commit_activity.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制提交活动图时出错: {e}")
            plt.close()
    
    def plot_code_growth(self, structure_metrics):
        """绘制代码规模增长"""
        if structure_metrics.empty:
            print("警告: 结构指标数据为空，无法绘制代码增长图")
            return
            
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        try:
            # 总文件数增长
            if 'date' in structure_metrics.columns and 'total_files' in structure_metrics.columns:
                axes[0, 0].plot(structure_metrics['date'], structure_metrics['total_files'], 
                               linewidth=2, label='Total Files')
                
                if 'source_files' in structure_metrics.columns:
                    axes[0, 0].plot(structure_metrics['date'], structure_metrics['source_files'], 
                                   linewidth=2, label='Source Files', alpha=0.7)
                    
                axes[0, 0].set_title('File Count Growth', fontsize=14, fontweight='bold')
                axes[0, 0].set_xlabel('Date')
                axes[0, 0].set_ylabel('Number of Files')
                axes[0, 0].legend()
                axes[0, 0].grid(True, alpha=0.3)
            
            # 总行数增长
            if 'date' in structure_metrics.columns and 'total_lines' in structure_metrics.columns:
                axes[0, 1].plot(structure_metrics['date'], structure_metrics['total_lines'], 
                               linewidth=2, color='red')
                axes[0, 1].set_title('Total Lines of Code', fontsize=14, fontweight='bold')
                axes[0, 1].set_xlabel('Date')
                axes[0, 1].set_ylabel('Lines of Code')
                axes[0, 1].grid(True, alpha=0.3)
            
            # 源文件与测试文件比例
            if ('date' in structure_metrics.columns and 
                'source_files' in structure_metrics.columns and 
                'total_files' in structure_metrics.columns and
                'test_files' in structure_metrics.columns):
                
                axes[1, 0].plot(structure_metrics['date'], 
                               structure_metrics['source_files'] / structure_metrics['total_files'],
                               linewidth=2, label='Source Files Ratio')
                axes[1, 0].plot(structure_metrics['date'], 
                               structure_metrics['test_files'] / structure_metrics['total_files'],
                               linewidth=2, label='Test Files Ratio')
                axes[1, 0].set_title('File Type Ratio Over Time', fontsize=14, fontweight='bold')
                axes[1, 0].set_xlabel('Date')
                axes[1, 0].set_ylabel('Ratio')
                axes[1, 0].legend()
                axes[1, 0].grid(True, alpha=0.3)
            
            # 平均文件大小
            if 'date' in structure_metrics.columns and 'avg_file_size' in structure_metrics.columns:
                axes[1, 1].plot(structure_metrics['date'], structure_metrics['avg_file_size'], 
                               linewidth=2, color='purple')
                axes[1, 1].set_title('Average File Size', fontsize=14, fontweight='bold')
                axes[1, 1].set_xlabel('Date')
                axes[1, 1].set_ylabel('Lines per File')
                axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.figures_dir / 'code_growth.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制代码增长图时出错: {e}")
            plt.close()
    
    def plot_filetype_evolution(self, filetype_evolution):
        """绘制文件类型演化"""
        try:
            # 转换为长格式便于绘图
            if 'date' not in filetype_evolution.columns:
                print("警告: 文件类型演化数据缺少日期列")
                return
                
            # 找出所有的文件类型列
            filetype_cols = [col for col in filetype_evolution.columns 
                            if col not in ['date', 'commit_hash']]
            
            if not filetype_cols:
                print("警告: 没有找到文件类型数据列")
                return
            
            # 创建堆积面积图
            plt.figure(figsize=(12, 6))
            
            pivot_data = filetype_evolution.set_index('date')[filetype_cols]
            
            plt.stackplot(pivot_data.index, 
                         [pivot_data[col] for col in filetype_cols],
                         labels=filetype_cols,
                         alpha=0.8)
            
            plt.title('File Type Evolution Over Time', fontsize=16, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Number of Files')
            plt.legend(loc='upper left')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.figures_dir / 'filetype_evolution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制文件类型演化图时出错: {e}")
            plt.close()
    
    def plot_test_coverage_trend(self, test_metrics):
        """绘制测试覆盖率趋势"""
        if test_metrics.empty:
            print("警告: 测试指标数据为空")
            return
            
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # 测试文件数量
            if 'date' in test_metrics.columns and 'total_test_files' in test_metrics.columns:
                axes[0, 0].plot(test_metrics['date'], test_metrics['total_test_files'], 
                               linewidth=2, marker='o', markersize=3)
                axes[0, 0].set_title('Test Files', fontsize=14, fontweight='bold')
                axes[0, 0].set_xlabel('Date')
                axes[0, 0].set_ylabel('Number of Test Files')
                axes[0, 0].grid(True, alpha=0.3)
            
            # 测试行数
            if 'date' in test_metrics.columns and 'total_test_lines' in test_metrics.columns:
                axes[0, 1].plot(test_metrics['date'], test_metrics['total_test_lines'], 
                               linewidth=2, color='green', marker='s', markersize=3)
                axes[0, 1].set_title('Test Lines of Code', fontsize=14, fontweight='bold')
                axes[0, 1].set_xlabel('Date')
                axes[0, 1].set_ylabel('Lines of Test Code')
                axes[0, 1].grid(True, alpha=0.3)
            
            # 测试比例
            if ('date' in test_metrics.columns and 
                'test_ratio_files' in test_metrics.columns and
                'test_ratio_lines' in test_metrics.columns):
                
                axes[1, 0].plot(test_metrics['date'], test_metrics['test_ratio_files'], 
                               linewidth=2, color='red', marker='^', markersize=3, label='Files Ratio')
                axes[1, 0].plot(test_metrics['date'], test_metrics['test_ratio_lines'], 
                               linewidth=2, color='blue', marker='v', markersize=3, label='Lines Ratio')
                axes[1, 0].set_title('Test Coverage Ratio', fontsize=14, fontweight='bold')
                axes[1, 0].set_xlabel('Date')
                axes[1, 0].set_ylabel('Test Ratio')
                axes[1, 0].legend()
                axes[1, 0].grid(True, alpha=0.3)
            
            # 测试质量指标
            if 'date' in test_metrics.columns and 'avg_test_length' in test_metrics.columns:
                axes[1, 1].plot(test_metrics['date'], test_metrics['avg_test_length'], 
                               linewidth=2, color='purple', marker='d', markersize=3)
                axes[1, 1].set_title('Average Test Length', fontsize=14, fontweight='bold')
                axes[1, 1].set_xlabel('Date')
                axes[1, 1].set_ylabel('Lines per Test')
                axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.figures_dir / 'test_coverage_trend.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制测试覆盖率趋势图时出错: {e}")
            plt.close()
    
    def plot_structure_changes(self, structure_metrics):
        """绘制代码结构变化"""
        if structure_metrics.empty:
            print("警告: 结构指标数据为空")
            return
            
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # 源代码与测试代码比例
            if ('date' in structure_metrics.columns and 
                'source_lines' in structure_metrics.columns and
                'total_lines' in structure_metrics.columns and
                'test_lines' in structure_metrics.columns and
                'doc_lines' in structure_metrics.columns):
                
                axes[0, 0].plot(structure_metrics['date'], 
                               structure_metrics['source_lines'] / structure_metrics['total_lines'],
                               linewidth=2, label='Source Code Ratio')
                axes[0, 0].plot(structure_metrics['date'], 
                               structure_metrics['test_lines'] / structure_metrics['total_lines'],
                               linewidth=2, label='Test Code Ratio')
                axes[0, 0].plot(structure_metrics['date'], 
                               structure_metrics['doc_lines'] / structure_metrics['total_lines'],
                               linewidth=2, label='Documentation Ratio')
                axes[0, 0].set_title('Code Composition Over Time', fontsize=14, fontweight='bold')
                axes[0, 0].set_xlabel('Date')
                axes[0, 0].set_ylabel('Ratio')
                axes[0, 0].legend()
                axes[0, 0].grid(True, alpha=0.3)
            
            # 最大文件大小趋势
            if 'date' in structure_metrics.columns and 'max_file_size' in structure_metrics.columns:
                axes[0, 1].plot(structure_metrics['date'], structure_metrics['max_file_size'], 
                               linewidth=2, color='orange')
                axes[0, 1].set_title('Maximum File Size Evolution', fontsize=14, fontweight='bold')
                axes[0, 1].set_xlabel('Date')
                axes[0, 1].set_ylabel('Lines in Largest File')
                axes[0, 1].grid(True, alpha=0.3)
            
            # 增长率分析
            if len(structure_metrics) > 1 and 'total_lines' in structure_metrics.columns:
                growth_rate = structure_metrics['total_lines'].pct_change() * 100
                if 'date' in structure_metrics.columns:
                    axes[1, 0].bar(structure_metrics['date'][1:], growth_rate[1:], alpha=0.7)
                    axes[1, 0].set_title('Code Growth Rate (%)', fontsize=14, fontweight='bold')
                    axes[1, 0].set_xlabel('Date')
                    axes[1, 0].set_ylabel('Growth Rate %')
                    axes[1, 0].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.figures_dir / 'structure_changes.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制结构变化图时出错: {e}")
            plt.close()
    
    def plot_author_heatmap(self, commit_data):
        """绘制作者贡献热力图"""
        if commit_data.empty:
            print("警告: 提交数据为空")
            return
            
        try:
            # 按作者和时间统计贡献
            if 'author' not in commit_data.columns or 'date' not in commit_data.columns:
                print("警告: 缺少作者或日期列")
                return
            
            # 创建月度分组
            commit_data['year_month'] = commit_data['date'].dt.to_period('M')
            
            author_monthly = commit_data.groupby(['author', 'year_month']).size()
            author_monthly = author_monthly.unstack(fill_value=0)
            
            # 选择主要贡献者
            author_totals = commit_data.groupby('author').size()
            top_authors = author_totals.nlargest(15).index
            author_monthly = author_monthly.loc[top_authors]
            
            plt.figure(figsize=(15, 8))
            sns.heatmap(author_monthly, cmap='YlOrRd', cbar_kws={'label': 'Number of Commits'})
            plt.title('Author Contribution Heatmap (Top 15)', fontsize=16, fontweight='bold')
            plt.xlabel('Month')
            plt.ylabel('Author')
            plt.tight_layout()
            plt.savefig(self.figures_dir / 'author_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制作者热力图时出错: {e}")
            plt.close()