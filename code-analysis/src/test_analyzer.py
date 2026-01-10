"""
测试覆盖率分析模块
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
from tqdm import tqdm
import subprocess
import tempfile
import os
import shutil

class TestCoverageAnalyzer:
    def __init__(self, config):
        self.config = config
        self.repo_path = Path(config['project']['clone_path'])
        
    def analyze_test_coverage(self, commit_data):
        """
        分析测试覆盖率的演化
        简化版本：只分析当前版本，不进行历史检出
        """
        print("分析测试覆盖率演化...")
        
        if commit_data.empty:
            print("警告: 提交数据为空，无法分析测试覆盖率")
            return pd.DataFrame()
        
        # 只分析当前版本（最新版本）
        try:
            repo = self.repo_path
            metrics = self._analyze_test_at_current(repo)
            
            if metrics:
                return pd.DataFrame([metrics])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"分析测试覆盖率时出错: {e}")
            return pd.DataFrame()
    
    def _analyze_test_at_current(self, repo_path):
        """分析当前版本的测试情况（不检出历史版本）"""
        metrics = {
            'date': pd.Timestamp.now(),
            'commit_hash': 'current',
            'total_test_files': 0,
            'total_test_lines': 0,
            'total_source_files': 0,
            'total_source_lines': 0,
            'test_ratio_files': 0,
            'test_ratio_lines': 0
        }
        
        # 统计测试文件和源文件
        test_info = self._count_test_files(repo_path)
        source_info = self._count_source_files(repo_path)
        
        metrics.update(test_info)
        metrics.update(source_info)
        
        # 计算比例
        if metrics['total_source_files'] > 0:
            metrics['test_ratio_files'] = metrics['total_test_files'] / metrics['total_source_files']
        
        if metrics['total_source_lines'] > 0:
            metrics['test_ratio_lines'] = metrics['total_test_lines'] / metrics['total_source_lines']
        
        # 分析测试质量
        quality_metrics = self._analyze_test_quality(repo_path)
        metrics.update(quality_metrics)
        
        return metrics
    
    def _count_test_files(self, repo_dir):
        """统计测试文件"""
        test_files = 0
        test_lines = 0
        
        for root, dirs, files in os.walk(repo_dir):
            # 跳过.git目录
            if '.git' in root:
                continue
                
            for file in files:
                file_path = Path(root) / file
                
                if self._is_test_file(file_path):
                    test_files += 1
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            test_lines += sum(1 for _ in f)
                    except:
                        continue
        
        return {
            'total_test_files': test_files,
            'total_test_lines': test_lines
        }
    
    def _count_source_files(self, repo_dir):
        """统计源文件"""
        source_files = 0
        source_lines = 0
        
        for root, dirs, files in os.walk(repo_dir):
            # 跳过.git目录
            if '.git' in root:
                continue
                
            for file in files:
                file_path = Path(root) / file
                
                if file_path.suffix == '.py' and not self._is_test_file(file_path):
                    source_files += 1
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            source_lines += sum(1 for _ in f)
                    except:
                        continue
        
        return {
            'total_source_files': source_files,
            'total_source_lines': source_lines
        }
    
    def _is_test_file(self, file_path):
        """判断是否为测试文件"""
        name = file_path.name.lower()
        
        # 文件名包含test
        if 'test' in name and file_path.suffix == '.py':
            return True
        
        # 检查父目录
        for parent in file_path.parents:
            if 'test' in parent.name.lower() and file_path.suffix == '.py':
                return True
        
        return False
    
    def _analyze_test_quality(self, repo_dir):
        """分析测试质量"""
        quality = {
            'avg_test_length': 0,
            'test_functions': 0,
            'test_classes': 0,
            'assertions': 0
        }
        
        test_lengths = []
        
        for root, dirs, files in os.walk(repo_dir):
            # 跳过.git目录
            if '.git' in root:
                continue
                
            for file in files:
                if file.endswith('.py') and 'test' in file.lower():
                    file_path = Path(root) / file
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # 统计测试函数和类
                            func_count = len(re.findall(r'def test_', content))
                            class_count = len(re.findall(r'class.*Test', content))
                            assert_count = len(re.findall(r'assert ', content))
                            
                            quality['test_functions'] += func_count
                            quality['test_classes'] += class_count
                            quality['assertions'] += assert_count
                            
                            # 统计文件行数
                            lines = content.count('\n')
                            test_lengths.append(lines)
                            
                    except:
                        continue
        
        if test_lengths:
            quality['avg_test_length'] = np.mean(test_lengths)
        
        return quality