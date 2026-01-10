"""
Git仓库历史分析模块
分析Flask项目的提交历史、代码结构和演化模式
"""

import pandas as pd
from git import Repo
from git.exc import GitCommandError
from datetime import datetime, timezone
from pathlib import Path
from tqdm import tqdm
import re
from collections import defaultdict, Counter
import pytz

class GitRepositoryAnalyzer:
    def __init__(self, config):
        """初始化Git仓库分析器
        
        Args:
            config: 配置字典，包含仓库路径等信息
        """
        self.config = config
        self.repo_path = Path(config['project']['clone_path'])
        
        try:
            self.repo = Repo(self.repo_path)
            print(f"✓ Git仓库加载成功: {self.repo_path}")
        except Exception as e:
            print(f"✗ 无法加载Git仓库: {e}")
            raise
    
    def _categorize_commit(self, message):
        """根据提交信息分类
        
        Args:
            message: 提交信息字符串
            
        Returns:
            str: 提交类型 ('fix', 'feat', 'refactor', 'doc', 'test', 'style', 'perf', 'ci', 'build', 'chore', 'other')
        """
        if not message or not isinstance(message, str):
            return 'other'
        
        msg_lower = message.lower()
        
        # 定义分类关键词
        categories = {
            'fix': ['fix', 'bug', 'error', 'issue', '修复', 'bugfix', '解决', '补丁'],
            'feat': ['feat', 'feature', 'add', 'implement', '新增', '添加', '支持', '实现'],
            'refactor': ['refactor', 'cleanup', 'optimize', 'improve', '重构', '优化', '改进', '清理'],
            'doc': ['doc', 'readme', 'comment', 'changelog', '文档', '注释', '说明', '手册'],
            'test': ['test', 'coverage', '测试', 'unittest', 'pytest', '测试用例'],
            'style': ['style', 'format', 'lint', '格式', '样式', '美化', '排版'],
            'perf': ['perf', 'performance', '性能', '优化', '加速'],
            'ci': ['ci', 'travis', 'github', 'workflow', '部署', '自动化', '集成'],
            'build': ['build', '打包', '编译', '构建', '依赖'],
            'chore': ['chore', '工具', '配置', '杂项', '清理']
        }
        
        # 检查每个分类的关键词
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in msg_lower:
                    return category
        
        return 'other'
    
    def _safe_datetime_conversion(self, date_obj):
        """安全转换日期时间对象 - 修复核心问题
        
        Args:
            date_obj: 原始日期时间对象
            
        Returns:
            datetime: 转换后的datetime对象
        """
        # GitPython 3.1.41 返回的已经是 datetime 对象
        if isinstance(date_obj, datetime):
            # 移除时区信息，避免pandas警告
            if date_obj.tzinfo is not None:
                # 转换为UTC时间，然后移除时区信息
                date_obj = date_obj.astimezone(timezone.utc).replace(tzinfo=None)
            return date_obj
        
        # 如果是其他类型，尝试转换
        try:
            # 转换为字符串
            date_str = str(date_obj)
            
            # 处理常见格式
            date_formats = [
                '%Y-%m-%d %H:%M:%S %z',
                '%Y-%m-%d %H:%M:%S',
                '%a %b %d %H:%M:%S %Y %z',
                '%a %b %d %H:%M:%S %Y',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S',
            ]
            
            for fmt in date_formats:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    if parsed.tzinfo is not None:
                        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                    return parsed
                except ValueError:
                    continue
            
            # 使用pandas解析
            parsed = pd.to_datetime(date_str, errors='coerce', utc=True)
            if pd.isna(parsed):
                raise ValueError(f"无法解析日期: {date_str}")
            
            # 转换为无时区的datetime
            if parsed.tz is not None:
                parsed = parsed.tz_convert('UTC').tz_localize(None)
            else:
                parsed = parsed.to_pydatetime()
            
            return parsed
            
        except Exception as e:
            print(f"日期转换警告: {e}, 使用默认日期")
            return datetime.now()
    
    def extract_commit_history(self, max_commits=None):
        """提取提交历史信息 - 修复日期问题
        
        Args:
            max_commits: 最大提交数限制，None表示无限制
            
        Returns:
            DataFrame: 包含提交信息的DataFrame
        """
        try:
            # 获取所有提交
            if max_commits:
                all_commits = list(self.repo.iter_commits(max_count=max_commits))
            else:
                all_commits = list(self.repo.iter_commits())
            
            print(f"发现 {len(all_commits)} 个提交")
            
            commits = []
            error_count = 0
            error_types = defaultdict(int)
            
            # 使用进度条
            pbar = tqdm(all_commits, desc="提取提交信息", unit="提交")
            
            for commit in pbar:
                try:
                    # 获取原始日期对象
                    raw_date = commit.committed_datetime
                    
                    # 安全转换日期
                    date_obj = self._safe_datetime_conversion(raw_date)
                    
                    # 获取统计信息
                    files_changed = 0
                    insertions = 0
                    deletions = 0
                    lines_changed = 0
                    
                    try:
                        if commit.stats and commit.stats.files:
                            files_changed = len(commit.stats.files)
                        
                        if hasattr(commit.stats, 'total'):
                            stats_total = commit.stats.total
                            insertions = stats_total.get('insertions', 0)
                            deletions = stats_total.get('deletions', 0)
                            lines_changed = stats_total.get('lines', 0)
                    except Exception as stats_error:
                        # 统计信息获取失败，但继续处理
                        pass
                    
                    # 构建提交信息
                    commit_info = {
                        'hash': commit.hexsha[:12],
                        'author': str(commit.author) if commit.author else 'Unknown',
                        'author_email': getattr(commit.author, 'email', '') if commit.author else '',
                        'date': date_obj,
                        'message': (commit.message or '').strip()[:500],
                        'files_changed': files_changed,
                        'insertions': insertions,
                        'deletions': deletions,
                        'lines_changed': lines_changed,
                    }
                    
                    # 分析提交类型
                    commit_info['commit_type'] = self._categorize_commit(commit_info['message'])
                    
                    # 获取修改的文件列表
                    try:
                        commit_info['modified_files'] = list(commit.stats.files.keys()) if commit.stats.files else []
                    except:
                        commit_info['modified_files'] = []
                    
                    commits.append(commit_info)
                    
                except Exception as e:
                    error_count += 1
                    error_type = type(e).__name__
                    error_types[error_type] += 1
                    
                    # 只显示前3个详细错误
                    if error_count <= 3:
                        print(f"  警告: 提交 {commit.hexsha[:12]} 处理失败: {e}")
                    
                    continue
            
            # 错误统计
            if error_count > 0:
                print(f"\n提交处理完成，成功: {len(commits)}, 失败: {error_count}")
                if error_types:
                    print("错误类型统计:")
                    for err_type, count in error_types.items():
                        print(f"  {err_type}: {count}次")
            
            # 创建DataFrame
            if not commits:
                print("警告: 没有成功处理任何提交")
                return pd.DataFrame()
            
            df = pd.DataFrame(commits)
            print(f"✓ 成功处理 {len(df)} 个提交")
            
            # 转换日期列为datetime - 这里非常重要！
            # 使用统一时区处理
            df['date'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
            
            # 移除无效日期
            invalid_dates = df['date'].isna().sum()
            if invalid_dates > 0:
                print(f"警告: 移除了 {invalid_dates} 个无效日期的提交")
                df = df.dropna(subset=['date'])
            
            # 转换为无时区的时间（避免pandas警告）
            df['date'] = df['date'].dt.tz_convert('UTC').dt.tz_localize(None)
            
            # 按日期排序
            if not df.empty:
                df = df.sort_values('date')
            
            # 添加时间维度
            if not df.empty and 'date' in df.columns:
                try:
                    df['year'] = df['date'].dt.year
                    df['month'] = df['date'].dt.month
                    df['year_month'] = df['date'].dt.to_period('M')
                    df['quarter'] = df['date'].dt.to_period('Q')
                    df['day_of_week'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday
                    
                    # 添加友好日期显示
                    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
                    
                except Exception as e:
                    print(f"添加时间维度时警告: {e}")
            
            # 基本统计信息
            if not df.empty:
                print(f"时间范围: {df['date'].min().strftime('%Y-%m-%d')} 到 {df['date'].max().strftime('%Y-%m-%d')}")
                print(f"作者数量: {df['author'].nunique()}")
                print(f"平均每次提交修改文件数: {df['files_changed'].mean():.1f}")
                
                # 提交类型统计
                if 'commit_type' in df.columns:
                    type_counts = df['commit_type'].value_counts()
                    print("\n提交类型分布:")
                    for type_name, count in type_counts.items():
                        percentage = count / len(df) * 100
                        print(f"  {type_name}: {count} ({percentage:.1f}%)")
            
            return df
            
        except Exception as e:
            print(f"提取提交历史时发生严重错误: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_commit_frequency(self, df, freq='M'):
        """获取提交频率统计
        
        Args:
            df: 包含提交数据的DataFrame
            freq: 统计频率 ('D':天, 'W':周, 'M':月, 'Q':季度, 'Y':年)
            
        Returns:
            Series: 按频率统计的提交数量
        """
        if df.empty or 'date' not in df.columns:
            print("警告: 数据为空或无日期列")
            return pd.Series()
        
        try:
            # 设置日期为索引并按频率重采样
            df_temp = df.copy()
            df_temp.set_index('date', inplace=True)
            return df_temp.resample(freq).size()
        except Exception as e:
            print(f"计算提交频率时出错: {e}")
            return pd.Series()
    
    def analyze_authors_contribution(self, df):
        """分析作者贡献度
        
        Args:
            df: 包含提交数据的DataFrame
            
        Returns:
            DataFrame: 作者贡献统计
        """
        if df.empty:
            print("警告: 数据为空")
            return pd.DataFrame()
        
        try:
            # 按作者分组统计
            author_stats = df.groupby('author').agg({
                'hash': 'count',
                'lines_changed': 'sum',
                'files_changed': 'sum',
                'insertions': 'sum',
                'deletions': 'sum'
            }).rename(columns={'hash': 'commit_count'})
            
            # 计算贡献比例
            total_commits = author_stats['commit_count'].sum()
            author_stats['contribution_ratio'] = author_stats['commit_count'] / total_commits * 100
            
            # 添加排名
            author_stats['rank'] = author_stats['commit_count'].rank(method='min', ascending=False).astype(int)
            
            # 计算净代码变化
            author_stats['net_changes'] = author_stats['insertions'] - author_stats['deletions']
            
            # 按提交数排序
            author_stats = author_stats.sort_values('commit_count', ascending=False)
            
            # 显示主要贡献者
            print(f"总作者数: {len(author_stats)}")
            if len(author_stats) > 0:
                print("\nTop 10 贡献者:")
                top_authors = author_stats.head(10)
                for idx, (author, stats) in enumerate(top_authors.iterrows(), 1):
                    print(f"  {idx:2d}. {author[:30]:30s} 提交: {stats['commit_count']:4d} "
                          f"({stats['contribution_ratio']:5.1f}%) 行变更: {stats['lines_changed']:6d}")
            
            return author_stats
            
        except Exception as e:
            print(f"分析作者贡献时出错: {e}")
            return pd.DataFrame()
    
    def extract_file_history(self, file_path):
        """提取单个文件的历史变更
        
        Args:
            file_path: 文件相对路径
            
        Returns:
            DataFrame: 文件变更历史
        """
        file_history = []
        
        try:
            # 获取文件的提交历史
            commits = list(self.repo.iter_commits(paths=file_path))
            
            if not commits:
                print(f"文件 {file_path} 在仓库中未找到历史记录")
                return pd.DataFrame()
            
            print(f"找到文件 {file_path} 的 {len(commits)} 个历史提交")
            
            for commit in tqdm(commits, desc=f"分析文件历史: {file_path}"):
                try:
                    # 处理日期
                    raw_date = commit.committed_datetime
                    date_obj = self._safe_datetime_conversion(raw_date)
                    
                    file_info = {
                        'commit_hash': commit.hexsha[:12],
                        'date': date_obj,
                        'author': str(commit.author) if commit.author else 'Unknown',
                        'message': (commit.message or '').strip()[:200],
                        'file_path': file_path
                    }
                    
                    # 获取文件变更详情
                    try:
                        if commit.parents:
                            diff = commit.diff(commit.parents[0], paths=file_path, create_patch=True)
                        else:
                            diff = commit.diff(None, paths=file_path, create_patch=True)
                        
                        if diff:
                            diff_item = diff[0]
                            file_info['changes'] = str(diff_item)[:1000]  # 限制长度
                            file_info['change_type'] = self._get_change_type(diff_item)
                            
                            # 统计变更行数
                            try:
                                patch_str = diff_item.diff.decode('utf-8', errors='ignore') if diff_item.diff else ''
                                added = len([line for line in patch_str.split('\n') if line.startswith('+') and not line.startswith('+++')])
                                removed = len([line for line in patch_str.split('\n') if line.startswith('-') and not line.startswith('---')])
                                file_info['lines_added'] = added
                                file_info['lines_removed'] = removed
                            except:
                                file_info['lines_added'] = 0
                                file_info['lines_removed'] = 0
                        else:
                            file_info['changes'] = ''
                            file_info['change_type'] = 'unknown'
                            file_info['lines_added'] = 0
                            file_info['lines_removed'] = 0
                            
                    except Exception as diff_error:
                        file_info['changes'] = ''
                        file_info['change_type'] = 'error'
                        file_info['lines_added'] = 0
                        file_info['lines_removed'] = 0
                    
                    file_history.append(file_info)
                    
                except Exception as e:
                    print(f"处理文件历史提交失败: {e}")
                    continue
            
            # 转换为DataFrame
            if file_history:
                df = pd.DataFrame(file_history)
                df['date'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
                if df['date'].dt.tz is not None:
                    df['date'] = df['date'].dt.tz_convert('UTC').dt.tz_localize(None)
                df = df.sort_values('date')
                return df
            else:
                return pd.DataFrame()
                
        except GitCommandError:
            print(f"文件 {file_path} 在仓库中不存在")
            return pd.DataFrame()
        except Exception as e:
            print(f"提取文件历史时出错: {e}")
            return pd.DataFrame()
    
    def _get_change_type(self, diff_item):
        """获取变更类型
        
        Args:
            diff_item: git diff对象
            
        Returns:
            str: 变更类型 ('added', 'deleted', 'renamed', 'modified')
        """
        try:
            if diff_item.new_file:
                return 'added'
            elif diff_item.deleted_file:
                return 'deleted'
            elif diff_item.renamed:
                return 'renamed'
            else:
                return 'modified'
        except:
            return 'unknown'
    
    def analyze_commit_size_distribution(self, df):
        """分析提交大小分布
        
        Args:
            df: 包含提交数据的DataFrame
            
        Returns:
            dict: 提交大小统计信息
        """
        if df.empty:
            return {}
        
        stats = {}
        
        try:
            # 按文件数分类
            files_col = 'files_changed'
            if files_col in df.columns:
                small = df[df[files_col] <= 3].shape[0]
                medium = df[(df[files_col] > 3) & (df[files_col] <= 10)].shape[0]
                large = df[df[files_col] > 10].shape[0]
                
                stats['files_changed_dist'] = {
                    'small (1-3 files)': small,
                    'medium (4-10 files)': medium,
                    'large (>10 files)': large
                }
            
            # 按行数分类
            lines_col = 'lines_changed'
            if lines_col in df.columns:
                tiny = df[df[lines_col] <= 10].shape[0]
                small = df[(df[lines_col] > 10) & (df[lines_col] <= 50)].shape[0]
                medium = df[(df[lines_col] > 50) & (df[lines_col] <= 200)].shape[0]
                large = df[df[lines_col] > 200].shape[0]
                
                stats['lines_changed_dist'] = {
                    'tiny (1-10 lines)': tiny,
                    'small (11-50 lines)': small,
                    'medium (51-200 lines)': medium,
                    'large (>200 lines)': large
                }
            
            # 统计量
            if 'files_changed' in df.columns:
                stats['files_stats'] = {
                    'mean': df['files_changed'].mean(),
                    'median': df['files_changed'].median(),
                    'max': df['files_changed'].max(),
                    'min': df['files_changed'].min(),
                    'std': df['files_changed'].std()
                }
            
            if 'lines_changed' in df.columns:
                stats['lines_stats'] = {
                    'mean': df['lines_changed'].mean(),
                    'median': df['lines_changed'].median(),
                    'max': df['lines_changed'].max(),
                    'min': df['lines_changed'].min(),
                    'std': df['lines_changed'].std()
                }
            
            return stats
            
        except Exception as e:
            print(f"分析提交大小分布时出错: {e}")
            return {}
    
    def analyze_temporal_patterns(self, df):
        """分析时间模式
        
        Args:
            df: 包含提交数据的DataFrame
            
        Returns:
            dict: 时间模式统计
        """
        if df.empty or 'date' not in df.columns:
            return {}
        
        patterns = {}
        
        try:
            # 按小时分析
            df['hour'] = df['date'].dt.hour
            
            # 按工作日分析
            df['weekday'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # 工作日提交统计
            weekday_counts = df['weekday'].value_counts().sort_index()
            weekday_stats = {weekday_names[i]: count for i, count in weekday_counts.items()}
            patterns['weekday_distribution'] = weekday_stats
            
            # 小时提交统计
            hour_counts = df['hour'].value_counts().sort_index()
            patterns['hour_distribution'] = hour_counts.to_dict()
            
            # 高峰时间
            if not hour_counts.empty:
                peak_hour = hour_counts.idxmax()
                patterns['peak_hour'] = peak_hour
            
            # 最活跃的工作日
            if not weekday_counts.empty:
                peak_weekday = weekday_counts.idxmax()
                patterns['peak_weekday'] = weekday_names[peak_weekday]
            
            return patterns
            
        except Exception as e:
            print(f"分析时间模式时出错: {e}")
            return {}