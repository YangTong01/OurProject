"""
代码结构分析模块
分析代码结构变化、文件类型演化等
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict
from tqdm import tqdm
import os

class CodeStructureAnalyzer:
    def __init__(self, config):
        self.config = config
        self.repo_path = Path(config['project']['clone_path'])
        
    def analyze_structure_evolution(self, commit_data, sample_points=50):
        """
        分析代码结构随时间的变化
        """
        print("Analyzing code structure evolution...")
        
        # 获取关键时间点的快照
        timeline = self._create_analysis_timeline(commit_data, sample_points)
        
        structure_metrics = []
        
        for idx, (commit_hash, date) in enumerate(tqdm(timeline, desc="Analyzing commits")):
            try:
                # 切换到该提交
                repo = self._get_repo_at_commit(commit_hash)
                
                # 分析代码结构
                metrics = self._analyze_code_snapshot(repo, date)
                metrics['commit_hash'] = commit_hash
                metrics['date'] = date
                
                structure_metrics.append(metrics)
                
            except Exception as e:
                print(f"Error analyzing commit {commit_hash}: {e}")
                continue
        
        return pd.DataFrame(structure_metrics)
    
    def analyze_filetype_evolution(self, commit_data):
        """
        分析文件类型随时间的变化
        """
        print("Analyzing file type evolution...")
        
        # 获取关键时间点的快照
        timeline = self._create_analysis_timeline(commit_data, 30)
        
        filetype_evolution = []
        
        for commit_hash, date in tqdm(timeline, desc="Analyzing file types"):
            try:
                repo = self._get_repo_at_commit(commit_hash)
                
                # 统计文件类型
                filetype_counts = self._count_filetypes(repo)
                
                # 添加时间信息
                filetype_counts['date'] = date
                filetype_counts['commit_hash'] = commit_hash
                
                filetype_evolution.append(filetype_counts)
                
            except Exception as e:
                print(f"Error at commit {commit_hash}: {e}")
                continue
        
        return pd.concat(filetype_evolution, ignore_index=True)
    
    def _create_analysis_timeline(self, commit_data, n_points):
        """创建分析时间线（均匀采样）"""
        commits = commit_data.sort_values('date')
        
        if len(commits) <= n_points:
            return list(zip(commits['hash'], commits['date']))
        
        # 均匀采样
        indices = np.linspace(0, len(commits)-1, n_points, dtype=int)
        sampled_commits = commits.iloc[indices]
        
        return list(zip(sampled_commits['hash'], sampled_commits['date']))
    
    def _get_repo_at_commit(self, commit_hash):
        """获取特定提交时的仓库状态"""
        import subprocess
        import tempfile
        
        # 临时检出到特定提交
        temp_dir = tempfile.mkdtemp()
        
        # 使用git archive导出文件
        cmd = f"git --git-dir={self.repo_path}/.git archive {commit_hash} | tar -x -C {temp_dir}"
        subprocess.run(cmd, shell=True, capture_output=True)
        
        return Path(temp_dir)
    
    def _analyze_code_snapshot(self, repo_path, date):
        """分析代码快照的结构"""
        metrics = {
            'total_files': 0,
            'total_lines': 0,
            'source_files': 0,
            'source_lines': 0,
            'test_files': 0,
            'test_lines': 0,
            'doc_files': 0,
            'doc_lines': 0,
            'avg_file_size': 0,
            'max_file_size': 0
        }
        
        file_sizes = []
        
        # 遍历所有文件
        for file_path in repo_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                # 统计文件类型
                file_type = self._categorize_file(file_path)
                
                # 统计行数
                try:
                    lines = self._count_lines(file_path)
                except:
                    lines = 0
                
                # 更新指标
                metrics['total_files'] += 1
                metrics['total_lines'] += lines
                
                if file_type == 'source':
                    metrics['source_files'] += 1
                    metrics['source_lines'] += lines
                elif file_type == 'test':
                    metrics['test_files'] += 1
                    metrics['test_lines'] += lines
                elif file_type == 'documentation':
                    metrics['doc_files'] += 1
                    metrics['doc_lines'] += lines
                
                file_sizes.append(lines)
        
        # 计算统计量
        if file_sizes:
            metrics['avg_file_size'] = np.mean(file_sizes)
            metrics['max_file_size'] = np.max(file_sizes)
        
        return metrics
    
    def _categorize_file(self, file_path):
        """分类文件类型"""
        file_name = file_path.name.lower()
        file_ext = file_path.suffix.lower()
        
        # 配置文件
        config_exts = ['.yml', '.yaml', '.toml', '.cfg', '.ini']
        if file_ext in config_exts or file_name in ['pyproject.toml', 'setup.cfg']:
            return 'config'
        
        # 测试文件
        if 'test' in file_name or file_name.endswith('_test.py'):
            return 'test'
        
        # Python源文件
        if file_ext == '.py':
            # 检查是否在测试目录中
            for parent in file_path.parents:
                if 'test' in parent.name.lower():
                    return 'test'
            return 'source'
        
        # 文档文件
        doc_exts = ['.md', '.rst', '.txt', '.tex']
        if file_ext in doc_exts:
            return 'documentation'
        
        return 'other'
    
    def _count_lines(self, file_path):
        """统计文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def _count_filetypes(self, repo_path):
        """统计各种文件类型的数量"""
        filetype_counts = defaultdict(int)
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                file_type = self._categorize_file(file_path)
                filetype_counts[file_type] += 1
        
        # 转换为DataFrame格式
        df_data = {k: [v] for k, v in filetype_counts.items()}
        return pd.DataFrame(df_data)
    
    def analyze_directory_structure(self, commit_data):
        """分析目录结构演化"""
        print("Analyzing directory structure evolution...")
        
        timeline = self._create_analysis_timeline(commit_data, 20)
        dir_evolution = []
        
        for commit_hash, date in tqdm(timeline, desc="Analyzing directories"):
            try:
                repo = self._get_repo_at_commit(commit_hash)
                
                # 分析目录结构
                dir_stats = self._analyze_directory_hierarchy(repo)
                dir_stats['date'] = date
                dir_stats['commit_hash'] = commit_hash
                
                dir_evolution.append(dir_stats)
                
            except Exception as e:
                print(f"Error at commit {commit_hash}: {e}")
                continue
        
        return pd.concat(dir_evolution, ignore_index=True)
    
    def _analyze_directory_hierarchy(self, repo_path):
        """分析目录层级结构"""
        stats = {
            'total_dirs': 0,
            'max_depth': 0,
            'avg_depth': 0,
            'dirs_by_level': defaultdict(int)
        }
        
        depths = []
        
        for root, dirs, files in os.walk(repo_path):
            # 计算深度
            depth = len(Path(root).relative_to(repo_path).parts)
            depths.append(depth)
            
            stats['total_dirs'] += 1
            stats['dirs_by_level'][depth] += 1
        
        if depths:
            stats['max_depth'] = max(depths)
            stats['avg_depth'] = np.mean(depths)
        
        # 展平字典以便存储
        for depth in range(stats['max_depth'] + 1):
            stats[f'dirs_level_{depth}'] = stats['dirs_by_level'].get(depth, 0)
        
        del stats['dirs_by_level']
        
        return stats