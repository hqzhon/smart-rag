#!/usr/bin/env python3
"""
配置审计脚本
检查硬编码配置和TODO项目
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class ConfigAuditor:
    """配置审计器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        
    def audit_hardcoded_values(self) -> List[Dict]:
        """检查硬编码值"""
        hardcoded_patterns = [
            (r'localhost', '硬编码localhost地址'),
            (r'127\.0\.0\.1', '硬编码本地IP地址'),
            (r'sk-[a-zA-Z0-9]{48}', '硬编码OpenAI API密钥'),
            (r'postgresql://[^"\']+', '硬编码数据库连接字符串'),
            (r'redis://[^"\']+', '硬编码Redis连接字符串'),
            (r'http://[^"\']+', '硬编码HTTP URL'),
            (r'https://[^"\']+', '硬编码HTTPS URL'),
        ]
        
        issues = []
        
        for py_file in self.project_root.rglob('*.py'):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in hardcoded_patterns:
                        if re.search(pattern, line) and not line.strip().startswith('#'):
                            issues.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': description,
                                'type': 'hardcoded'
                            })
            except Exception as e:
                print(f"读取文件失败 {py_file}: {e}")
                
        return issues
    
    def audit_todo_items(self) -> List[Dict]:
        """检查TODO项目"""
        todo_patterns = [
            (r'TODO:', 'TODO项目'),
            (r'FIXME:', 'FIXME项目'),
            (r'HACK:', 'HACK项目'),
            (r'XXX:', 'XXX项目'),
        ]
        
        issues = []
        
        for py_file in self.project_root.rglob('*.py'):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in todo_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': description,
                                'type': 'todo'
                            })
            except Exception as e:
                print(f"读取文件失败 {py_file}: {e}")
                
        return issues
    
    def audit_env_usage(self) -> List[Dict]:
        """检查环境变量使用"""
        issues = []
        env_pattern = r'os\.getenv\(["\']([^"\']+)["\']'
        
        for py_file in self.project_root.rglob('*.py'):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    matches = re.findall(env_pattern, line)
                    for env_var in matches:
                        # 检查是否在.env.example中定义
                        env_example_path = self.project_root / '.env.example'
                        if env_example_path.exists():
                            env_content = env_example_path.read_text()
                            if env_var not in env_content:
                                issues.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'issue': f'环境变量 {env_var} 未在.env.example中定义',
                                    'type': 'env_missing'
                                })
            except Exception as e:
                print(f"读取文件失败 {py_file}: {e}")
                
        return issues
    
    def generate_report(self) -> str:
        """生成审计报告"""
        hardcoded_issues = self.audit_hardcoded_values()
        todo_issues = self.audit_todo_items()
        env_issues = self.audit_env_usage()
        
        report = []
        report.append("# 配置审计报告")
        report.append(f"生成时间: {os.popen('date').read().strip()}")
        report.append("")
        
        # 硬编码问题
        if hardcoded_issues:
            report.append("## 🚨 硬编码配置问题")
            report.append("")
            for issue in hardcoded_issues:
                report.append(f"**{issue['file']}:{issue['line']}**")
                report.append(f"- 问题: {issue['issue']}")
                report.append(f"- 代码: `{issue['content']}`")
                report.append("")
        else:
            report.append("## ✅ 硬编码配置检查")
            report.append("未发现硬编码配置问题")
            report.append("")
        
        # TODO项目
        if todo_issues:
            report.append("## 📝 待完成项目")
            report.append("")
            for issue in todo_issues:
                report.append(f"**{issue['file']}:{issue['line']}**")
                report.append(f"- 类型: {issue['issue']}")
                report.append(f"- 内容: `{issue['content']}`")
                report.append("")
        else:
            report.append("## ✅ 待完成项目检查")
            report.append("未发现待完成项目")
            report.append("")
        
        # 环境变量问题
        if env_issues:
            report.append("## ⚠️ 环境变量配置问题")
            report.append("")
            for issue in env_issues:
                report.append(f"**{issue['file']}:{issue['line']}**")
                report.append(f"- 问题: {issue['issue']}")
                report.append(f"- 代码: `{issue['content']}`")
                report.append("")
        else:
            report.append("## ✅ 环境变量配置检查")
            report.append("环境变量配置正常")
            report.append("")
        
        # 统计信息
        report.append("## 📊 统计信息")
        report.append(f"- 硬编码问题: {len(hardcoded_issues)}")
        report.append(f"- 待完成项目: {len(todo_issues)}")
        report.append(f"- 环境变量问题: {len(env_issues)}")
        report.append(f"- 总计问题: {len(hardcoded_issues) + len(todo_issues) + len(env_issues)}")
        
        return "\n".join(report)

def main():
    """主函数"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auditor = ConfigAuditor(project_root)
    
    print("🔍 开始配置审计...")
    report = auditor.generate_report()
    
    # 保存报告
    report_path = os.path.join(project_root, "CONFIG_AUDIT_REPORT.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📄 审计报告已保存到: {report_path}")
    print("\n" + "="*50)
    print(report)

if __name__ == "__main__":
    main()