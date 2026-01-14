"""
程序静态分析
"""
import os
import ast
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# 三个模块的定义
MODULES = {
    'flask': {
        'name': 'Flask核心源码分析',
        'description': 'Flask框架源代码的质量分析',
        'include_patterns': ['flask/'],
        'exclude_patterns': ['__pycache__/', 'venv/', '.git/', '.tox/', 'tests/',
                           'examples/', 'docs/', 'benchmarks/']
    },
    'data_analysis': {
        'name': '基础统计分析',
        'description': '负责Flask项目的活跃度、时间趋势等基础分析',
        'include_patterns': ['analysis_basic.py', 'collect_git.py', 'preprocess.py',
                             'utils.py', 'main.py', 'src/', 'data/', 'figures/'],
        'exclude_patterns': ['flask/', '__pycache__/', 'venv/', '.git/', 'test_', '_test.py']
    },
    'commit_analysis': {
        'name': '贡献者分析',
        'description': '负责贡献者排名、社区结构、开发模式分析',
        'include_patterns': ['analytics/', 'routes/', 'collector/', 'tools/',
                             'debug.py', 'repo.py', 'stats.py', 'models.py',
                             'run.py', 'data/', 'reports/'],
        'exclude_patterns': ['flask/', '__pycache__/', 'venv/', '.git/']
    },
    'code-analysis': {
        'name': '代码演化分析',
        'description': '负责代码结构、测试覆盖、文件类型演化分析',
        'include_patterns': ['code_analyzer.py', 'create_final_fix.py', 'fix_git_date.py',
                             'git_analyzer.py', 'test_analyzer.py', 'utils.py',
                             'visualization.py', 'basic_analysis.py', 'main.py',
                             'src/', 'data/', 'figures/', 'reports/'],
        'exclude_patterns': ['flask/', '__pycache__/', 'venv/', '.git/']
    }
}


class FixedModuleAnalyzer:
    """修复版模块分析器"""

    def __init__(self):
        self.results = {}
        self.comparison_data = []

    def should_include_file(self, filepath, module_info):
        """判断是否应该包含此文件"""
        rel_path = filepath.replace('\\', '/')  # 统一路径分隔符

        # 检查排除模式
        for exclude in module_info['exclude_patterns']:
            if exclude in rel_path:
                return False

        # 检查包含模式
        for include in module_info['include_patterns']:
            if include.endswith('/'):  # 目录
                if rel_path.startswith(include):
                    return True
            else:  # 文件
                if rel_path == include or rel_path.endswith('/' + include):
                    return True

        # 对于src目录下的所有.py文件都包含
        if 'src/' in rel_path and rel_path.endswith('.py'):
            return True

        # 根目录下的.py文件也包含（但排除flask等）
        if '/' not in rel_path and rel_path.endswith('.py'):
            # 检查文件名是否包含排除关键词
            excluded_keywords = ['test', '_test', 'flask']
            if not any(keyword in rel_path.lower() for keyword in excluded_keywords):
                return True

        return False

    def analyze_all_modules(self):
        """分析所有模块（flask和我们的三个模块）"""
        print("=" * 70)
        print("静态分析模块")
        print("=" * 70)

        for module_dir01, module_info in MODULES.items():
            # 构建完整路径
            if module_dir01 == 'flask':
                # flask在static_analysis目录下
                module_dir = os.path.join('.', module_dir01)  # ./flask
            else:
                # 其他模块在上一级目录
                module_dir = os.path.join('..', module_dir01)  # ../data_analysis

            if not os.path.exists(module_dir):
                print(f"\n 模块 {module_dir} 不存在，跳过")
                continue

            print(f"\n{'=' * 40}")
            print(f"分析模块: {module_dir} ({module_info['name']})")
            print(f"{'=' * 40}")

            # 分析单个模块
            module_results = self.analyze_single_module(module_dir, module_info)
            self.results[module_dir] = module_results

            # 添加到对比数据
            if module_results['summary']['function_count'] > 0:
                self.comparison_data.append({
                    'module': module_dir,
                    'display_name': module_info['name'],
                    **module_results['summary']
                })
            else:
                print(f" {module_dir} 模块未发现函数，可能配置有误")

        if len(self.comparison_data) >= 2:
            # 生成对比报告
            self.generate_comparison_report()
        elif self.comparison_data:
            print(f"\n⚠只有一个模块有数据，跳过对比分析")
        else:
            print(f"\n所有模块都没有发现函数，请检查配置")

        print(f"\n{'=' * 70}")
        print("分析完成！")
        print(f"{'=' * 70}")

    def analyze_single_module(self, module_dir, module_info):
        """分析单个模块"""
        # 1. 先分析文件
        print("分析文件结构...")
        file_analysis = self.analyze_module_files(module_dir, module_info)

        # 2. 分析复杂度（使用file_analysis中的文件列表）
        print("分析代码复杂度...")
        complexity = self.analyze_module_complexity(module_dir, module_info, file_analysis)

        # 3. 分析结构
        print("分析模块结构...")
        structure = self.analyze_module_structure(module_dir, module_info, file_analysis)

        # 4. 分析依赖
        print("分析模块依赖...")
        dependencies = self.analyze_module_dependencies(module_dir, module_info, file_analysis)

        # 5. 组合结果
        results = {
            'info': module_info,
            'file_analysis': file_analysis,
            'complexity': complexity,
            'structure': structure,
            'dependencies': dependencies,
            'summary': {}
        }

        # 6. 生成摘要统计
        results['summary'] = self.generate_module_summary(results)

        # 7. 输出模块报告
        self.print_module_report(module_dir, results)

        # 8. 保存详细结果
        self.save_module_results(module_dir, results)

        return results

    def analyze_module_files(self, module_dir, module_info):
        """分析模块文件结构"""
        file_analysis = {
            'total_files': 0,
            'included_files': [],
            'excluded_files': [],
            'python_files': [],
            'other_files': [],
            'file_categories': defaultdict(list)
        }

        # 扫描所有文件
        for root, dirs, files in os.walk(module_dir):
            # 先过滤目录
            dirs_to_remove = []
            for d in dirs:
                dir_path = os.path.join(root, d).replace('\\', '/')
                rel_dir = os.path.relpath(dir_path, module_dir).replace('\\', '/')

                # 检查是否应该排除
                exclude = False
                for pattern in module_info['exclude_patterns']:
                    if pattern in rel_dir or pattern in dir_path:
                        exclude = True
                        break

                if exclude:
                    dirs_to_remove.append(d)

            # 移除要排除的目录
            for d in dirs_to_remove:
                dirs.remove(d)

            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, module_dir).replace('\\', '/')

                file_analysis['total_files'] += 1

                # 判断是否应该包含
                if self.should_include_file(rel_path, module_info):
                    file_analysis['included_files'].append(rel_path)

                    if file.endswith('.py'):
                        file_analysis['python_files'].append(rel_path)

                        # 分类文件
                        if 'test' in file.lower() or '_test' in rel_path.lower():
                            category = '测试文件'
                        elif 'util' in file.lower() or 'helper' in file.lower():
                            category = '工具函数'
                        elif 'main' in file.lower() or file == 'run.py':
                            category = '入口文件'
                        elif 'visual' in file.lower() or 'plot' in file.lower():
                            category = '可视化'
                        elif 'config' in file.lower():
                            category = '配置'
                        else:
                            category = '核心代码'

                        file_analysis['file_categories'][category].append(rel_path)
                    else:
                        file_analysis['other_files'].append(rel_path)
                else:
                    file_analysis['excluded_files'].append(rel_path)

        # 输出统计
        print(f"  总文件数: {file_analysis['total_files']}")
        print(f"  包含的文件: {len(file_analysis['included_files'])}")
        print(f"  排除的文件: {len(file_analysis['excluded_files'])}")
        print(f"  Python文件: {len(file_analysis['python_files'])}")
        print(f"  其他文件: {len(file_analysis['other_files'])}")

        # 显示包含的文件
        if file_analysis['python_files']:
            print(f"  包含的Python文件:")
            for file in file_analysis['python_files'][:10]:  # 最多显示10个
                print(f"    • {file}")
            if len(file_analysis['python_files']) > 10:
                print(f"    • ... 等 {len(file_analysis['python_files']) - 10} 个文件")
        else:
            print(f"  ！  未找到Python文件，请检查include_patterns配置")
            print(f"  当前配置: {module_info['include_patterns']}")

        return file_analysis

    def analyze_module_complexity(self, module_dir, module_info, file_analysis):
        """分析模块代码复杂度"""
        complexity_data = {
            'functions': [],
            'overall': {
                'function_count': 0,
                'total_complexity': 0,
                'avg_complexity': 0,
                'max_complexity': 0,
                'high_complexity_funcs': [],
                'functions_without_doc': 0
            }
        }

        # 只分析包含的Python文件
        python_files = file_analysis.get('python_files', [])

        if not python_files:
            print(" 没有Python文件可分析！")
            return complexity_data

        for rel_path in python_files:
            filepath = os.path.join(module_dir, rel_path.replace('/', os.sep))

            # print(f"  正在分析: {rel_path}")

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 检查文件内容
                if not content.strip():
                    print(f"     文件为空: {rel_path}")
                    continue

                tree = ast.parse(content)

                # 分析函数
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_complexity = self.calculate_cyclomatic_complexity(node)

                        func_info = {
                            'name': node.name,
                            'file': rel_path,
                            'line': node.lineno,
                            'complexity': func_complexity,
                            'has_docstring': ast.get_docstring(node) is not None,
                            'arg_count': len(node.args.args)
                        }

                        complexity_data['functions'].append(func_info)
                        complexity_data['overall']['function_count'] += 1
                        complexity_data['overall']['total_complexity'] += func_complexity

                        if func_complexity > complexity_data['overall']['max_complexity']:
                            complexity_data['overall']['max_complexity'] = func_complexity

                        if func_complexity > 10:  # 高复杂度
                            complexity_data['overall']['high_complexity_funcs'].append(func_info)

                        if not func_info['has_docstring']:
                            complexity_data['overall']['functions_without_doc'] += 1

            except SyntaxError as e:
                print(f" 语法错误 {rel_path}: {e}")
                continue
            except UnicodeDecodeError as e:
                print(f" 编码错误 {rel_path}: {e}")
                continue
            except Exception as e:
                print(f" 分析失败 {rel_path}: {e}")
                continue

        # 计算平均复杂度
        if complexity_data['overall']['function_count'] > 0:
            complexity_data['overall']['avg_complexity'] = (
                    complexity_data['overall']['total_complexity'] /
                    complexity_data['overall']['function_count']
            )

        # 输出结果
        print(f"  函数总数: {complexity_data['overall']['function_count']}")
        if complexity_data['overall']['function_count'] > 0:
            print(f"  平均复杂度: {complexity_data['overall']['avg_complexity']:.2f}")
            print(f"  最高复杂度: {complexity_data['overall']['max_complexity']}")
            print(f"  高复杂度函数: {len(complexity_data['overall']['high_complexity_funcs'])} 个")
            print(f"  缺少文档的函数: {complexity_data['overall']['functions_without_doc']} 个")

        return complexity_data

    def calculate_cyclomatic_complexity(self, node):
        """计算圈复杂度"""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1

        return complexity

    def analyze_module_structure(self, module_dir, module_info, file_analysis):
        """分析模块结构"""
        structure_data = {
            'has_init_files': False,
            'has_main_entry': False,
            'has_config_files': False,
            'has_test_structure': False,
            'directory_depth': 0
        }

        # 检查包含的文件
        included_files = file_analysis.get('included_files', [])

        for rel_path in included_files:
            # 检查是否是__init__.py
            if rel_path.endswith('__init__.py'):
                structure_data['has_init_files'] = True

            # 检查是否是入口文件
            if any(name in rel_path for name in ['main.py', 'run.py', 'app.py']):
                structure_data['has_main_entry'] = True

            # 检查是否是配置文件
            if any(name in rel_path for name in ['config', '.yaml', '.yml', '.ini']):
                structure_data['has_config_files'] = True

            # 检查是否有测试结构
            if 'test' in rel_path.lower():
                structure_data['has_test_structure'] = True

            # 计算目录深度
            depth = rel_path.count('/')
            if depth > structure_data['directory_depth']:
                structure_data['directory_depth'] = depth

        # 输出结构信息
        print(f"  目录深度: {structure_data['directory_depth']}")
        print(f"  有__init__.py: {'是' if structure_data['has_init_files'] else '否'}")
        print(f"  有配置文件: {'是' if structure_data['has_config_files'] else '否'}")
        print(f"  有测试文件: {'是' if structure_data['has_test_structure'] else '否'}")
        print(f"  有主入口: {'是' if structure_data['has_main_entry'] else '否'}")

        return structure_data

    def analyze_module_dependencies(self, module_dir, module_info, file_analysis):
        """分析模块依赖"""
        dependencies = {
            'external_imports': set(),
            'standard_lib_imports': set(),
            'import_counts': defaultdict(int),
            'module_imports': defaultdict(list)
        }

        standard_libs = {
            'os', 'sys', 'json', 'time', 'datetime', 'math', 're', 'collections',
            'itertools', 'functools', 'pathlib', 'typing', 'logging', 'subprocess'
        }

        common_data_libs = {
            'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
            'sklearn', 'scipy', 'networkx'
        }

        web_frameworks = {
            'flask', 'django', 'fastapi', 'tornado', 'bottle'
        }

        # 只分析包含的Python文件
        python_files = file_analysis.get('python_files', [])

        for rel_path in python_files:
            filepath = os.path.join(module_dir, rel_path.replace('/', os.sep))

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if not content.strip():
                    continue

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module_name = alias.name.split('.')[0]
                            dependencies['import_counts'][module_name] += 1
                            dependencies['module_imports'][rel_path].append(module_name)

                            if module_name in standard_libs:
                                dependencies['standard_lib_imports'].add(module_name)
                            else:
                                dependencies['external_imports'].add(module_name)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_name = node.module.split('.')[0]
                            dependencies['import_counts'][module_name] += 1
                            dependencies['module_imports'][rel_path].append(module_name)

                            if module_name in standard_libs:
                                dependencies['standard_lib_imports'].add(module_name)
                            else:
                                dependencies['external_imports'].add(module_name)

            except Exception as e:
                continue

        # 分类外部依赖
        categorized_deps = {
            '数据分析库': [],
            'Web框架': [],
            '其他': []
        }

        for dep in dependencies['external_imports']:
            if dep in common_data_libs:
                categorized_deps['数据分析库'].append(dep)
            elif dep in web_frameworks:
                categorized_deps['Web框架'].append(dep)
            else:
                categorized_deps['其他'].append(dep)

        # 输出依赖信息
        print(f"  外部依赖总数: {len(dependencies['external_imports'])}")

        for category, deps in categorized_deps.items():
            if deps:
                print(f"  {category}: {len(deps)} 个")
                if len(deps) <= 3:
                    print(f"    • {', '.join(deps)}")

        print(f"  标准库依赖: {len(dependencies['standard_lib_imports'])} 个")

        # 找出最常用的导入
        if dependencies['import_counts']:
            top_imports = sorted(
                dependencies['import_counts'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            print(f"  最常用导入:")
            for module, count in top_imports:
                print(f"    • {module}: {count} 次")

        dependencies['categorized'] = categorized_deps
        return dependencies

    def generate_module_summary(self, results):
        """生成模块摘要"""
        file_analysis = results['file_analysis']
        complexity = results['complexity']['overall']
        structure = results['structure']

        doc_coverage = 0
        if complexity['function_count'] > 0:
            doc_coverage = (1 - complexity['functions_without_doc'] / complexity['function_count']) * 100

        summary = {
            'python_file_count': len(file_analysis['python_files']),
            'total_file_count': len(file_analysis['included_files']),
            'function_count': complexity['function_count'],
            'avg_complexity': complexity['avg_complexity'],
            'max_complexity': complexity['max_complexity'],
            'high_complexity_count': len(complexity['high_complexity_funcs']),
            'doc_coverage': doc_coverage,
            'has_main_entry': structure['has_main_entry'],
            'has_tests': structure['has_test_structure'],
            'has_config': structure['has_config_files'],
            'directory_depth': structure['directory_depth'],
            'external_deps_count': len(results['dependencies']['external_imports'])
        }

        return summary

    def print_module_report(self, module_dir, results):
        """打印模块报告"""
        info = results['info']
        summary = results['summary']

        print(f"\n {module_dir} 模块报告 ({info['name']})")
        print(f"描述: {info['description']}")
        print(f"{'=' * 50}")

        print(f"规模指标:")
        print(f"  • 包含文件: {summary['total_file_count']} 个")
        print(f"  • Python文件: {summary['python_file_count']} 个")
        print(f"  • 函数数量: {summary['function_count']} 个")

        if summary['function_count'] > 0:
            print(f"\n质量指标:")
            print(f"  • 平均复杂度: {summary['avg_complexity']:.2f}")
            if summary['avg_complexity'] > 7:
                print(f"      复杂度较高")
            print(f"  • 最高复杂度: {summary['max_complexity']}")
            print(f"  • 高复杂度函数: {summary['high_complexity_count']} 个")
            print(f"  • 文档覆盖率: {summary['doc_coverage']:.1f}%")
            if summary['doc_coverage'] < 50:
                print(f"      文档覆盖率较低")

        print(f"\n工程实践:")
        print(f"  • 有主入口: {' 是' if summary['has_main_entry'] else ' 否'}")
        print(f"  • 有测试文件: {' 是' if summary['has_tests'] else ' 否'}")
        print(f"  • 有配置文件: {' 是' if summary['has_config'] else ' 否'}")
        print(f"  • 目录深度: {summary['directory_depth']}")
        print(f"  • 外部依赖: {summary['external_deps_count']} 个")

        # 特别提示
        if summary['function_count'] == 0:
            print(f"\n 警告: 未找到任何函数")
            print(f"  可能的原因:")
            print(f"  1. 过滤规则过严，请检查include_patterns配置")
            print(f"  2. 文件确实没有函数")
            print(f"  3. 文件编码问题导致无法解析")

    def save_module_results(self, module_dir, results):
        """保存模块结果"""
        output_dir = f"results/module_analysis/{module_dir}"
        os.makedirs(output_dir, exist_ok=True)

        # 保存JSON数据
        with open(f"{output_dir}/analysis_results.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        # 生成并保存报告
        report = self.generate_module_text_report(module_dir, results)
        with open(f"{output_dir}/analysis_report.txt", 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"报告已保存: {output_dir}/")

    def generate_module_text_report(self, module_dir, results):
        """生成模块文本报告"""
        import time

        info = results['info']
        summary = results['summary']
        file_analysis = results['file_analysis']

        report = f"""
    {'=' * 70}
    {module_dir} - {info['name']} 分析报告
    {'=' * 70}

    模块概述
    {'-' * 40}
    模块名称: {module_dir}
    模块职责: {info['description']}
    分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
    分析范围: 只包含指定文件，已过滤Flask源码

    规模统计
    {'-' * 40}
    包含文件总数: {summary['total_file_count']}
    Python文件数: {summary['python_file_count']}
    函数数量: {summary['function_count']}
    目录深度: {summary['directory_depth']}
    """

        if summary['function_count'] > 0:
            report += f"""
    代码质量
    {'-' * 40}
    平均圈复杂度: {summary['avg_complexity']:.2f} ({' 较高' if summary['avg_complexity'] > 7 else '良好'})
    最高复杂度: {summary['max_complexity']} ({' 注意' if summary['max_complexity'] > 15 else '正常'})
    高复杂度函数(>10): {summary['high_complexity_count']} ({' 注意' if summary['high_complexity_count'] > 0 else '良好'})
    文档覆盖率: {summary['doc_coverage']:.1f}% ({'可能需改进' if summary['doc_coverage'] < 50 else '良好'})
    """
        else:
            report += """
    代码质量
    {'-' * 40}
    ⚠️ 未找到任何函数，无法计算质量指标
    """

        report += f"""
    工程实践
    {'-' * 40}
    主入口文件: {'[✓] 有' if summary['has_main_entry'] else '[✗] 无'}
    测试文件: {'[✓] 有' if summary['has_tests'] else '[✗] 无'}
    配置文件: {'[✓] 有' if summary['has_config'] else '[✗] 无'}
    外部依赖: {summary['external_deps_count']} 个

    详细分析
    {'=' * 70}

    文件结构
    {'-' * 40}
    包含的文件 ({len(file_analysis['included_files'])} 个):
    """

        # 列出包含的Python文件
        if file_analysis['python_files']:
            report += "\nPython文件:\n"
            for i, file in enumerate(file_analysis['python_files'][:10], 1):
                report += f"  {i:2d}. {file}\n"
            if len(file_analysis['python_files']) > 10:
                report += f"     ... 等 {len(file_analysis['python_files']) - 10} 个文件\n"

        # 文件分类
        if file_analysis['file_categories']:
            report += "\n文件分类:\n"
            for category, files in file_analysis['file_categories'].items():
                report += f"  • {category}: {len(files)} 个文件\n"

        # 复杂度详情
        complexity = results['complexity']['overall']
        if complexity['function_count'] > 0:
            report += f"""
    复杂度详情
    {'-' * 40}
    函数总数: {complexity['function_count']}
    缺少文档的函数: {complexity['functions_without_doc']} 个
    """

            if complexity['high_complexity_funcs']:
                report += "高复杂度函数列表:\n"
                for i, func in enumerate(complexity['high_complexity_funcs'][:5], 1):
                    report += f"  {i:2d}. {func['name']} (在 {func['file']}:{func['line']}) - 复杂度: {func['complexity']}\n"
                if len(complexity['high_complexity_funcs']) > 5:
                    report += f"     ... 等 {len(complexity['high_complexity_funcs']) - 5} 个高复杂度函数\n"
            else:
                report += "高复杂度函数: 无\n"

        # 依赖分析
        deps = results['dependencies']
        report += f"""
    依赖分析
    {'-' * 40}
    外部依赖总数: {len(deps['external_imports'])} 个
    """

        if deps.get('categorized'):
            for category, dep_list in deps['categorized'].items():
                if dep_list:
                    report += f"\n{category} ({len(dep_list)} 个):\n"
                    for dep in sorted(dep_list)[:5]:
                        report += f"  • {dep}\n"
                    if len(dep_list) > 5:
                        report += f"     ... 等 {len(dep_list) - 5} 个\n"

        report += f"""
    标准库依赖: {len(deps['standard_lib_imports'])} 个
    """

        # 最常用导入
        if deps['import_counts']:
            top_imports = sorted(deps['import_counts'].items(), key=lambda x: x[1], reverse=True)[:5]
            report += "\n最常用导入:\n"
            for i, (module, count) in enumerate(top_imports, 1):
                report += f"  {i:2d}. {module}: {count} 次\n"

        # 建议
        report += f"""
    评估与建议
    {'=' * 70}
    {self.generate_module_recommendations(summary)}

    {'=' * 70}
    生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}
    {'=' * 70}
    """

        return report

    def generate_module_recommendations(self, summary):
        """生成模块建议"""
        recommendations = []

        if summary['function_count'] == 0:
            recommendations.append("**未找到代码**: 可能是过滤规则过严，请检查include_patterns配置")
            return "\n".join(recommendations)

        if summary['avg_complexity'] > 8:
            recommendations.append(
                f"1. **降低复杂度**: 平均复杂度 {summary['avg_complexity']:.2f} 较高，建议重构复杂函数")
        elif summary['avg_complexity'] > 5:
            recommendations.append(f"2. **关注复杂度**: 平均复杂度 {summary['avg_complexity']:.2f}，建议保持关注")

        if summary['doc_coverage'] < 50:
            recommendations.append(f"3. **完善文档**: 文档覆盖率 {summary['doc_coverage']:.1f}%，建议添加函数文档字符串")
        elif summary['doc_coverage'] < 70:
            recommendations.append(f"4. **改进文档**: 文档覆盖率 {summary['doc_coverage']:.1f}%，建议补充关键函数文档")

        if summary['high_complexity_count'] > 0:
            recommendations.append(f"5. **重点关注**: 有 {summary['high_complexity_count']} 个高复杂度函数可能需要重构")

        if summary['external_deps_count'] > 15:
            recommendations.append(f"6. **依赖管理**: 外部依赖较多 ({summary['external_deps_count']} 个)，检查是否必要")

        if not recommendations:
            recommendations.append("**代码质量良好**: 复杂度适中，文档覆盖率良好，继续保持！")

        return "\n".join(recommendations)

    def generate_comparison_report(self):
        """生成对比报告"""
        if len(self.comparison_data) < 2:
            print("\n 可用于对比的模块不足2个，跳过对比分析")
            return

        print(f"\n{'=' * 50}")
        print("模块对比分析")
        print(f"{'=' * 50}")

        # 创建对比表格
        headers = ['模块', '文件数', '函数数', '平均复杂度', '文档覆盖率', '高复杂度', '外部依赖']

        print(f"\n{' | '.join(headers)}")
        print('-' * 70)

        for module_data in self.comparison_data:
            row = [
                module_data['display_name'],
                str(module_data['python_file_count']),
                str(module_data['function_count']),
                f"{module_data['avg_complexity']:.2f}",
                f"{module_data['doc_coverage']:.1f}%",
                str(module_data['high_complexity_count']),
                str(module_data['external_deps_count'])
            ]
            print(' | '.join(row))

        # 生成对比可视化
        self.plot_module_comparison()

        # 保存对比报告
        self.save_comparison_report()

    def plot_module_comparison(self):
        """绘制模块对比图"""
        try:
            if len(self.comparison_data) < 2:
                return

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            # 使用模块标识符而不是中文名称
            modules = ['flask', 'data_analysis', 'commit_analysis', 'code-analysis']

            # 过滤出实际存在的模块
            existing_modules = []
            module_indices = []
            for i, module_id in enumerate(modules):
                # 查找对应的数据
                for data in self.comparison_data:
                    if data['module'].endswith(module_id) or module_id in data['module']:
                        existing_modules.append(module_id)
                        module_indices.append(i)
                        break

            if len(existing_modules) < 2:
                print("⚠️  可用于对比的模块不足2个，跳过绘图")
                return

            # 准备数据
            file_counts = []
            func_counts = []
            complexities = []
            doc_coverages = []

            for module_id in existing_modules:
                for data in self.comparison_data:
                    if data['module'].endswith(module_id) or module_id in data['module']:
                        file_counts.append(data['python_file_count'])
                        func_counts.append(data['function_count'])
                        complexities.append(data['avg_complexity'])
                        doc_coverages.append(data['doc_coverage'])
                        break

            # 1. Python文件数量对比
            colors1 = plt.cm.Blues(np.linspace(0.5, 0.9, len(existing_modules)))
            bars1 = axes[0, 0].bar(existing_modules, file_counts, color=colors1, edgecolor='black')
            axes[0, 0].set_title('Python File Count', fontsize=12, fontweight='bold')
            axes[0, 0].set_ylabel('Number of Files')
            axes[0, 0].tick_params(axis='x', rotation=15)

            for i, count in enumerate(file_counts):
                axes[0, 0].text(i, count + 0.1, str(count), ha='center', va='bottom', fontsize=10)

            # 2. 函数数量对比
            colors2 = plt.cm.Greens(np.linspace(0.5, 0.9, len(existing_modules)))
            bars2 = axes[0, 1].bar(existing_modules, func_counts, color=colors2, edgecolor='black')
            axes[0, 1].set_title('Function Count', fontsize=12, fontweight='bold')
            axes[0, 1].set_ylabel('Number of Functions')
            axes[0, 1].tick_params(axis='x', rotation=15)

            for i, count in enumerate(func_counts):
                axes[0, 1].text(i, count + 0.1, str(count), ha='center', va='bottom', fontsize=10)

            # 3. 复杂度对比
            colors3 = plt.cm.Reds(np.linspace(0.5, 0.9, len(existing_modules)))
            bars3 = axes[1, 0].bar(existing_modules, complexities, color=colors3, edgecolor='black')
            axes[1, 0].set_title('Average Complexity', fontsize=12, fontweight='bold')
            axes[1, 0].set_ylabel('Avg Complexity')
            axes[1, 0].axhline(y=7, color='red', linestyle='--', alpha=0.5, label='Suggested (7)')
            axes[1, 0].legend()
            axes[1, 0].tick_params(axis='x', rotation=15)

            for i, comp in enumerate(complexities):
                axes[1, 0].text(i, comp + 0.05, f'{comp:.2f}', ha='center', va='bottom', fontsize=10)

            # 4. 文档覆盖率对比
            colors4 = plt.cm.Purples(np.linspace(0.5, 0.9, len(existing_modules)))
            bars4 = axes[1, 1].bar(existing_modules, doc_coverages, color=colors4, edgecolor='black')
            axes[1, 1].set_title('Documentation Coverage', fontsize=12, fontweight='bold')
            axes[1, 1].set_ylabel('Doc Coverage (%)')
            axes[1, 1].axhline(y=70, color='green', linestyle='--', alpha=0.5, label='Suggested (70%)')
            axes[1, 1].legend()
            axes[1, 1].tick_params(axis='x', rotation=15)

            for i, coverage in enumerate(doc_coverages):
                axes[1, 1].text(i, coverage + 0.5, f'{coverage:.1f}%', ha='center', va='bottom', fontsize=10)

            plt.suptitle('Module Comparison Analysis', fontsize=16, fontweight='bold', y=1.02)
            plt.tight_layout()

            # 保存图片
            os.makedirs('../results', exist_ok=True)
            plt.savefig('results/module_comparison.png', dpi=300, bbox_inches='tight')
            plt.show()

            print(f"\nComparison chart saved: results/module_comparison.png")

        except Exception as e:
            print(f"Failed to draw comparison chart: {e}")

    def save_comparison_report(self):
        """保存对比报告"""
        report = self.generate_comparison_text_report()  # 修改方法名

        with open('./results/module_comparison_report.txt', 'w', encoding='utf-8') as f:  # 改为.txt
            f.write(report)

        print(f"对比报告已保存: results/module_comparison_report.txt")

    def generate_comparison_text_report(self):
        """生成对比文本报告"""
        import time

        report = f"""
    {'=' * 80}
    分工模块质量对比报告
    {'=' * 80}

    分析概述
    {'-' * 40}
    分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
    分析模块: {len(self.comparison_data)} 个
    分析范围: 只分析指定文件，已过滤Flask源码
    分析维度: 规模、复杂度、文档、工程实践

    模块职责说明
    {'-' * 40}
    """

        for module_dir, module_info in MODULES.items():
            if module_dir in self.results:
                report += f"模块目录: {module_dir}\n模块名称: {module_info['name']}\n主要职责: {module_info['description']}\n{'-' * 40}\n"

        report += f"""
    详细对比
    {'=' * 80}

    规模对比
    {'-' * 40}
    模块              Python文件数  函数数量  目录深度
    """

        for data in self.comparison_data:
            report += f"{data['display_name']:<16} {data['python_file_count']:<12} {data['function_count']:<10} {data.get('directory_depth', 0)}\n"

        report += f"""
    质量对比
    {'-' * 40}
    模块              平均复杂度  最高复杂度  高复杂度函数  文档覆盖率
    """

        for data in self.comparison_data:
            complexity_mark = "！" if data['avg_complexity'] > 7 else "✓"
            doc_mark = "！" if data['doc_coverage'] < 50 else "✓"
            report += f"{data['display_name']:<16} {data['avg_complexity']:<11.2f}{complexity_mark} {data['max_complexity']:<11} {data['high_complexity_count']:<13} {data['doc_coverage']:<8.1f}%{doc_mark}\n"

        report += f"""
    工程实践对比
    {'-' * 40}
    模块              主入口  测试文件  配置文件  外部依赖
    """

        for data in self.comparison_data:
            main_entry = "✓" if data['has_main_entry'] else "✗"
            tests = "✓" if data['has_tests'] else "✗"
            config = "✓" if data['has_config'] else "✗"
            report += f"{data['display_name']:<16} {main_entry:<8} {tests:<9} {config:<9} {data['external_deps_count']}\n"

        # 分析发现
        report += f"""
    主要发现
    {'=' * 80}
    {self.generate_comparison_insights()}

    综合建议
    {'=' * 80}
    {self.generate_comparison_recommendations()}

    可视化图表
    {'-' * 40}
    对比图表文件: module_comparison.png
    (详细对比图表见 results/module_comparison.png)

    {'=' * 80}
    生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}
    {'=' * 80}
    """

        return report

    def generate_comparison_insights(self):
        """生成对比发现"""
        if not self.comparison_data:
            return "无对比数据"

        insights = []

        # 找出规模最大的模块
        largest_module = max(self.comparison_data, key=lambda x: x['python_file_count'])
        insights.append(
            f"1. **规模最大**: {largest_module['display_name']} 模块，有 {largest_module['python_file_count']} 个Python文件")

        # 找出函数最多的模块
        most_funcs = max(self.comparison_data, key=lambda x: x['function_count'])
        insights.append(f"2. **函数最多**: {most_funcs['display_name']} 模块，有 {most_funcs['function_count']} 个函数")

        # 找出最复杂的模块
        most_complex = max(self.comparison_data, key=lambda x: x['avg_complexity'])
        if most_complex['avg_complexity'] > 7:
            insights.append(
                f"3. **复杂度最高**: {most_complex['display_name']} 模块，平均复杂度 {most_complex['avg_complexity']:.2f} (超过建议阈值7)")

        # 找出文档最好的模块
        best_documented = max(self.comparison_data, key=lambda x: x['doc_coverage'])
        if best_documented['doc_coverage'] < 70:
            insights.append(
                f"4. **文档最佳**: {best_documented['display_name']} 模块，文档覆盖率 {best_documented['doc_coverage']:.1f}% (但仍低于70%建议值)")

        # 找出依赖最多的模块
        most_deps = max(self.comparison_data, key=lambda x: x['external_deps_count'])
        if most_deps['external_deps_count'] > 0:
            insights.append(
                f"5. **依赖最多**: {most_deps['display_name']} 模块，有 {most_deps['external_deps_count']} 个外部依赖")

        return "\n".join(insights)

    def generate_comparison_recommendations(self):
        """生成对比建议"""
        recommendations = []

        # 复杂度建议
        high_complex_modules = [m for m in self.comparison_data if m['avg_complexity'] > 7]
        if high_complex_modules:
            module_names = ', '.join([m['display_name'] for m in high_complex_modules])
            recommendations.append(f"1. **复杂度优化**: {module_names} 模块的复杂度超过建议阈值7，建议重构复杂函数")

        # 文档建议
        low_doc_modules = [m for m in self.comparison_data if m['doc_coverage'] < 50]
        if low_doc_modules:
            module_names = ', '.join([m['display_name'] for m in low_doc_modules])
            recommendations.append(f"2. **文档改进**: {module_names} 模块的文档覆盖率低于50%，急需补充文档")

        # 测试建议
        no_test_modules = [m for m in self.comparison_data if not m['has_tests']]
        if no_test_modules:
            module_names = ', '.join([m['display_name'] for m in no_test_modules])
            recommendations.append(f"3. **添加测试**: {module_names} 模块缺少测试文件，建议添加单元测试")

        # 其他建议
        recommendations.append("4. **代码复用**: 检查三个模块间是否有可复用的通用功能，避免重复代码")
        recommendations.append("5. **统一规范**: 建立统一的代码风格和工程实践标准")
        recommendations.append("6. **定期评审**: 组织代码评审会议，分享最佳实践")

        return "\n".join(recommendations)


def main():
    """主函数"""
    # 确保结果目录存在
    os.makedirs('../results', exist_ok=True)
    os.makedirs('../results/module_analysis', exist_ok=True)

    print(" 开始分析三个分工模块...")

    # 创建分析系统
    analyzer = FixedModuleAnalyzer()

    # 执行分析
    analyzer.analyze_all_modules()

    print(f"\n分析完成！")
    print(f"生成的成果:")
    print(f"1. 各模块详细报告: results/module_analysis/")
    print(f"2. 模块对比图: results/module_comparison.png")
    print(f"3. 对比报告: results/module_comparison_report.txt")


if __name__ == "__main__":
    # 导入时间模块
    import time
    # 运行主函数
    main()