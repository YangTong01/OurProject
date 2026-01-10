"""
工具函数模块
"""

import json
import yaml
import pickle
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import sys

def setup_logging(log_file="analysis.log"):
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def save_pickle(data, file_path):
    """保存数据为pickle格式"""
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

def load_pickle(file_path):
    """加载pickle数据"""
    with open(file_path, 'rb') as f:
        return pickle.load(f)

def save_json(data, file_path, indent=2):
    """保存数据为JSON格式"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

def load_json(file_path):
    """加载JSON数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_growth_rate(series):
    """计算增长率"""
    if len(series) < 2:
        return pd.Series([0] * len(series), index=series.index)
    
    return series.pct_change() * 100

def detect_outliers(data, threshold=3):
    """检测异常值"""
    mean = np.mean(data)
    std = np.std(data)
    
    outliers = np.abs(data - mean) > threshold * std
    return outliers

def time_series_smoothing(series, window=3):
    """时间序列平滑"""
    return series.rolling(window=window, center=True).mean()

def format_bytes(size):
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def ensure_directory(path):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)

def calculate_complexity_metrics(code_text):
    """计算代码复杂度指标（简化版）"""
    # 这里可以添加更复杂的代码分析逻辑
    lines = code_text.split('\n')
    
    metrics = {
        'total_lines': len(lines),
        'blank_lines': sum(1 for line in lines if line.strip() == ''),
        'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
        'import_lines': sum(1 for line in lines if line.strip().startswith('import') or line.strip().startswith('from')),
        'function_defs': sum(1 for line in lines if line.strip().startswith('def ')),
        'class_defs': sum(1 for line in lines if line.strip().startswith('class '))
    }
    
    metrics['code_lines'] = metrics['total_lines'] - metrics['blank_lines'] - metrics['comment_lines']
    metrics['comment_ratio'] = metrics['comment_lines'] / metrics['total_lines'] if metrics['total_lines'] > 0 else 0
    
    return metrics