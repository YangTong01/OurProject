# fix_git_date.py
import os

new_code = '''"""
Git仓库历史分析模块 - 修复日期问题版
"""

import pandas as pd
from git import Repo
from git.exc import GitCommandError
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import warnings

class GitRepositoryAnalyzer:
    def __init__(self, config):
        self.config = config
        self.repo_path = Path(config['project']['clone_path'])
        try:
            self.repo = Repo(self.repo_path)
            print(f"✓ Git仓库加载成功: {self.repo_path}")
        except Exception as e:
            print(f"✗ 无法加载Git仓库: {e}")
            raise
    
    def _categorize_commit(self, message):
        """根据提交信息分类"""
        if not message or not isinstance(message, str):
            return 'other'
        
        msg_lower = message.lower()
        
        # 定义分类关键词
        categories = {
            'fix': ['fix', 'bug', 'error', 'issue', '修复', 'bugfix'],
            'feat': ['feat', 'feature', 'add', 'implement', '新增', '添加', '支持'],
            'refactor': ['refactor', 'cleanup', 'optimize', 'improve', '重构', '优化', '改进'],
            'doc': ['doc', 'readme', 'comment', 'changelog', '文档', '注释', '说明'],
            'test': ['test', 'coverage', '测试', 'unittest', 'pytest'],
            'style': ['style', 'format', 'lint', '格式', '样式', '美化'],
            'perf': ['perf', 'performance', '性能', '优化'],
            'ci': ['ci', 'travis', 'github', 'workflow', '部署', '自动化'],
            'build': ['build', '打包', '编译', '构建'],
            'chore': ['chore', '工具', '配置', '杂项']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in msg_lower:
                    return category
        
        return 'other'
    
    def extract_commit_history(self, max_commits=None):
        """提取提交历史信息 - 修复版"""
        try:
            # 获取所有提交
            if max_commits:
                all_commits = list(self.repo.iter_commits(max_count=max_commits))
            else:
                all_commits = list(self.repo.iter_commits())
            
            print(f"发现 {len(all_commits)} 个提交")
            
            commits = []
            error_count = 0
            
            # 使用进度条
            pbar = tqdm(all_commits, desc="提取提交信息", unit="提交")
            
            for commit in pbar:
                try:
                    # 直接使用commit.committed_datetime，它已经是datetime对象
                    date_obj = commit.committed_datetime
                    
                    # 确保是datetime对象
                    if not isinstance(date_obj, datetime):
                        # 尝试转换
                        date_obj = pd.to_datetime(str(date_obj), errors='coerce')
                        if pd.isna(date_obj):
                            date_obj = datetime.now()
                    
                    # 获取统计信息
                    try:
                        files_changed = len(commit.stats.files) if commit.stats.files else 0
                        stats_total = getattr(commit.stats, 'total', {})
                        insertions = stats_total.get('insertions', 0)
                        deletions = stats_total.get('deletions', 0)
                        lines_changed = stats_total.get('lines', 0)
                    except:
                        files_changed = insertions = deletions = lines_changed = 0
                    
                    commit_info = {
                        'hash': commit.hexsha[:12],
                        'author': str(commit.author) if commit.author else 'Unknown',
                        'date': date_obj,
                        'message': (commit.message or '').strip()[:500],
                        'files_changed': files_changed,
                        'insertions': insertions,
                        'deletions': deletions,
                        'lines_changed': lines_changed,
                        'commit_type': self._categorize_commit(commit.message or ''),
                    }
                    
                    commits.append(commit_info)
                    
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        print(f"错误处理提交 {commit.hexsha[:12]}: {e}")
                    continue
            
            if error_count > 0:
                print(f"总共 {error_count} 个错误")
            
            # 创建DataFrame
            if not commits:
                print("警告: 没有成功处理任何提交")
                return pd.DataFrame()
            
            df = pd.DataFrame(commits)
            print(f"✓ 成功处理 {len(df)} 个提交")
            
            # 确保日期列是datetime类型
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # 移除无效日期
            invalid_count = df['date'].isna().sum()
            if invalid_count > 0:
                print(f"警告: {invalid_count} 个提交的日期无效")
                df = df.dropna(subset=['date'])
            
            if df.empty:
                print("警告: 所有提交的日期都无效")
                return df
            
            # 按日期排序
            df = df.sort_values('date')
            
            # 添加时间维度（避免时区警告）
            try:
                df['year'] = df['date'].dt.year
                df['month'] = df['date'].dt.month
                # 使用字符串格式避免时区警告
                df['year_month'] = df['date'].dt.strftime('%Y-%m')
                df['day_of_week'] = df['date'].dt.dayofweek
            except Exception as e:
                print(f"添加时间维度时警告: {e}")
            
            # 基本统计
            print(f"时间范围: {df['date'].min().strftime('%Y-%m-%d')} 到 {df['date'].max().strftime('%Y-%m-%d')}")
            print(f"作者数量: {df['author'].nunique()}")
            
            # 提交类型统计
            type_counts = df['commit_type'].value_counts()
            print("提交类型分布:")
            for type_name, count in type_counts.items():
                percentage = count / len(df) * 100
                print(f"  {type_name}: {count} ({percentage:.1f}%)")
            
            return df
            
        except Exception as e:
            print(f"提取提交历史时发生严重错误: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    # 其他方法保持不变...
    def get_commit_frequency(self, df, freq='M'):
        """获取提交频率统计"""
        if df.empty or 'date' not in df.columns:
            return pd.Series()
        
        try:
            df_temp = df.copy()
            df_temp.set_index('date', inplace=True)
            return df_temp.resample(freq).size()
        except Exception as e:
            print(f"计算提交频率时出错: {e}")
            return pd.Series()
    
    def analyze_authors_contribution(self, df):
        """分析作者贡献度"""
        if df.empty:
            return pd.DataFrame()
        
        try:
            author_stats = df.groupby('author').agg({
                'hash': 'count',
                'lines_changed': 'sum',
                'files_changed': 'sum'
            }).rename(columns={'hash': 'commit_count'})
            
            author_stats['contribution_ratio'] = author_stats['commit_count'] / author_stats['commit_count'].sum() * 100
            author_stats = author_stats.sort_values('commit_count', ascending=False)
            
            return author_stats
            
        except Exception as e:
            print(f"分析作者贡献时出错: {e}")
            return pd.DataFrame()
'''

# 写入文件
with open('src/git_analyzer.py', 'w', encoding='utf-8') as f:
    f.write(new_code)

print("已修复 git_analyzer.py 的日期转换问题")