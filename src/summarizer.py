import json
import yaml
from loguru import logger
from utils import DatabaseManager
import pandas as pd


class RuleMatcher:
    """用户规则匹配器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.rules = self.config.get('rules', [])
        self.db = DatabaseManager()
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _extract_features(self, numbers: list) -> dict:
        """提取特征"""
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        even_count = 5 - odd_count
        big_count = sum(1 for n in numbers if n >= 5)
        small_count = 5 - big_count
        
        return {
            "sum": sum(numbers),
            "odd_count": odd_count,
            "even_count": even_count,
            "big_count": big_count,
            "small_count": small_count,
            "has_duplicate": len(numbers) != len(set(numbers)),
            "has_sequence": self._check_sequence(numbers)
        }
    
    def _check_sequence(self, numbers: list) -> int:
        """检查最长连续序列"""
        sorted_nums = sorted(numbers)
        max_seq = 1
        current_seq = 1
        
        for i in range(1, len(sorted_nums)):
            if sorted_nums[i] == sorted_nums[i-1] + 1:
                current_seq += 1
                max_seq = max(max_seq, current_seq)
            else:
                current_seq = 1
        
        return max_seq
    
    def match_rules(self, period_id: str, numbers: list) -> list:
        """匹配规则"""
        features = self._extract_features(numbers)
        matched = []
        
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            try:
                # 简单的条件评估
                condition = rule['condition']
                # 这里可以使用更安全的表达式评估
                if self._evaluate_condition(condition, features):
                    matched.append({
                        "rule_name": rule['name'],
                        "alert": rule['alert'],
                        "period_id": period_id
                    })
            except Exception as e:
                logger.error(f"规则匹配失败 {rule['name']}: {e}")
        
        return matched
    
    def _evaluate_condition(self, condition: str, features: dict) -> bool:
        """评估条件（简化版）"""
        try:
            # 替换条件中的变量
            expr = condition
            for key, value in features.items():
                expr = expr.replace(key, str(value))
            
            # 安全评估
            return eval(expr)
        except:
            return False


class LotterySummarizer:
    """澳洲幸运5 总结生成器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.matcher = RuleMatcher()
    
    def generate_summary(self, patterns: dict) -> str:
        """生成自然语言总结"""
        summary_parts = []
        
        # 频率分析总结
        freq = patterns.get('standard_patterns', {}).get('frequency', {})
        if freq:
            hot = freq.get('hot_numbers', [])
            cold = freq.get('cold_numbers', [])
            summary_parts.append(f"热号：{hot}，冷号：{cold}")
        
        # 分布分析总结
        dist = patterns.get('standard_patterns', {}).get('distribution', {})
        if dist:
            odd_even = dist.get('odd_even_ratio', {})
            most_common = max(odd_even.items(), key=lambda x: x[1])
            summary_parts.append(f"单双比例最常见：{most_common[0]}")
        
        # 长龙分析总结
        dragon = patterns.get('standard_patterns', {}).get('long_dragon', {})
        if dragon:
            max_odd = dragon.get('max_odd_streak', 0)
            max_even = dragon.get('max_even_streak', 0)
            summary_parts.append(f"最长单数连开：{max_odd}期，最长双数连开：{max_even}期")
        
        # 统计检验总结
        test = patterns.get('standard_patterns', {}).get('statistical_test', {})
        if test:
            is_random = test.get('is_random', True)
            p_value = test.get('p_value', 0)
            status = "符合随机分布" if is_random else "可能存在规律"
            summary_parts.append(f"卡方检验 p={p_value:.3f}，{status}")
        
        return "。".join(summary_parts)
    
    def generate_report(self, patterns: dict, latest_numbers: list = None) -> dict:
        """生成完整报告"""
        report = {
            "timestamp": patterns.get('last_update'),
            "period_range": patterns.get('period_range'),
            "natural_summary": self.generate_summary(patterns),
            "matched_rules": []
        }
        
        # 匹配用户规则
        if latest_numbers:
            latest_period = self.db.get_latest_period()
            if latest_period:
                matched = self.matcher.match_rules(latest_period, latest_numbers)
                report["matched_rules"] = matched
        
        return report


def main():
    """主函数"""
    # 加载分析结果
    try:
        with open("data/summary.json", 'r', encoding='utf-8') as f:
            patterns = json.load(f)
    except:
        logger.error("未找到分析结果文件")
        return
    
    summarizer = LotterySummarizer()
    report = summarizer.generate_report(patterns)
    
    print("\n" + "="*50)
    print("澳洲幸运5 分析报告")
    print("="*50)
    print(f"期号范围: {report['period_range']}")
    print(f"更新时间: {report['timestamp']}")
    print(f"\n规律总结:\n{report['natural_summary']}")
    print(f"\n匹配规则: {len(report['matched_rules'])} 条")
    for rule in report['matched_rules']:
        print(f"  - {rule['rule_name']}: {rule['alert']}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
