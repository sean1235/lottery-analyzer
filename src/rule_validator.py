"""规则验证器 - 计算规则的有效度"""
import yaml
import pandas as pd
from loguru import logger
from utils import DatabaseManager
from summarizer import RuleMatcher


class RuleValidator:
    """规则有效性验证器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.db = DatabaseManager()
        self.matcher = RuleMatcher(config_path)
        self.df = None
    
    def load_data(self):
        """加载历史数据"""
        self.df = self.db.get_all_data()
        if self.df.empty:
            logger.warning("没有可用数据")
            return False
        
        # 解析号码
        self.df['numbers_list'] = self.df['numbers'].apply(
            lambda x: [int(n) for n in x.split(',')]
        )
        logger.info(f"已加载 {len(self.df)} 条数据用于验证")
        return True
    
    def validate_rule(self, rule: dict, window: int = None) -> dict:
        """验证单个规则的有效性"""
        if not self.load_data():
            return {}
        
        # 如果指定窗口，只验证最近的数据
        df_to_check = self.df.head(window) if window else self.df
        
        total_periods = len(df_to_check)
        matched_periods = []
        
        # 检查每一期是否匹配规则
        for idx, row in df_to_check.iterrows():
            period_id = row['period_id']
            numbers = row['numbers_list']
            
            matched = self.matcher.match_rules(period_id, numbers)
            
            # 检查是否匹配当前规则
            for match in matched:
                if match['rule_name'] == rule['name']:
                    matched_periods.append({
                        'period_id': period_id,
                        'numbers': numbers,
                        'draw_time': row['draw_time']
                    })
                    break
        
        # 计算统计指标
        hit_count = len(matched_periods)
        hit_rate = hit_count / total_periods if total_periods > 0 else 0
        
        # 计算连续命中和最长间隔
        max_streak = 0
        current_streak = 0
        max_gap = 0
        current_gap = 0
        
        for idx, row in df_to_check.iterrows():
            period_id = row['period_id']
            is_hit = any(m['period_id'] == period_id for m in matched_periods)
            
            if is_hit:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
                if current_gap > 0:
                    max_gap = max(max_gap, current_gap)
                current_gap = 0
            else:
                current_streak = 0
                current_gap += 1
        
        return {
            'rule_name': rule['name'],
            'description': rule.get('description', ''),
            'condition': rule['condition'],
            'total_periods': total_periods,
            'hit_count': hit_count,
            'hit_rate': round(hit_rate * 100, 2),  # 百分比
            'max_streak': max_streak,  # 最长连续命中
            'max_gap': max_gap,  # 最长未命中间隔
            'matched_periods': matched_periods[:10],  # 只返回最近10次命中
            'effectiveness': self._calculate_effectiveness(hit_rate, max_streak, max_gap)
        }
    
    def _calculate_effectiveness(self, hit_rate: float, max_streak: int, max_gap: int) -> str:
        """计算规则有效性等级"""
        # 综合评分
        score = 0
        
        # 命中率评分 (0-40分)
        if hit_rate >= 0.3:  # 30%以上
            score += 40
        elif hit_rate >= 0.2:  # 20-30%
            score += 30
        elif hit_rate >= 0.1:  # 10-20%
            score += 20
        else:
            score += hit_rate * 100
        
        # 连续性评分 (0-30分)
        if max_streak >= 5:
            score += 30
        elif max_streak >= 3:
            score += 20
        else:
            score += max_streak * 5
        
        # 稳定性评分 (0-30分) - 间隔越小越好
        if max_gap <= 5:
            score += 30
        elif max_gap <= 10:
            score += 20
        elif max_gap <= 20:
            score += 10
        else:
            score += max(0, 30 - max_gap)
        
        # 评级
        if score >= 80:
            return "⭐⭐⭐⭐⭐ 极高"
        elif score >= 60:
            return "⭐⭐⭐⭐ 高"
        elif score >= 40:
            return "⭐⭐⭐ 中等"
        elif score >= 20:
            return "⭐⭐ 较低"
        else:
            return "⭐ 低"
    
    def validate_all_rules(self, window: int = None) -> list:
        """验证所有规则"""
        results = []
        
        for rule in self.matcher.rules:
            if rule.get('enabled', True):
                result = self.validate_rule(rule, window)
                if result:
                    results.append(result)
        
        # 按命中率排序
        results.sort(key=lambda x: x['hit_rate'], reverse=True)
        return results
    
    def add_rule(self, rule: dict, config_path: str = "config.yaml") -> bool:
        """添加新规则到配置文件"""
        try:
            # 读取现有配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 添加新规则
            if 'rules' not in config:
                config['rules'] = []
            
            config['rules'].append(rule)
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"规则 '{rule['name']}' 已添加")
            return True
        except Exception as e:
            logger.error(f"添加规则失败: {e}")
            return False
    
    def update_rule(self, rule_name: str, updated_rule: dict, config_path: str = "config.yaml") -> bool:
        """更新规则"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 查找并更新规则
            for i, rule in enumerate(config.get('rules', [])):
                if rule['name'] == rule_name:
                    config['rules'][i] = updated_rule
                    break
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"规则 '{rule_name}' 已更新")
            return True
        except Exception as e:
            logger.error(f"更新规则失败: {e}")
            return False
    
    def delete_rule(self, rule_name: str, config_path: str = "config.yaml") -> bool:
        """删除规则"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 删除规则
            config['rules'] = [r for r in config.get('rules', []) if r['name'] != rule_name]
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"规则 '{rule_name}' 已删除")
            return True
        except Exception as e:
            logger.error(f"删除规则失败: {e}")
            return False


def main():
    """测试函数"""
    validator = RuleValidator()
    
    print("\n" + "="*60)
    print("规则有效性验证报告")
    print("="*60)
    
    results = validator.validate_all_rules(window=100)
    
    for result in results:
        print(f"\n规则名称: {result['rule_name']}")
        print(f"描述: {result['description']}")
        print(f"条件: {result['condition']}")
        print(f"验证期数: {result['total_periods']}")
        print(f"命中次数: {result['hit_count']}")
        print(f"命中率: {result['hit_rate']}%")
        print(f"最长连续命中: {result['max_streak']} 期")
        print(f"最长未命中间隔: {result['max_gap']} 期")
        print(f"有效性评级: {result['effectiveness']}")
        print("-" * 60)


if __name__ == "__main__":
    main()
