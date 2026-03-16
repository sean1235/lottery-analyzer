import pandas as pd
import numpy as np
from scipy import stats
from loguru import logger
from utils import DatabaseManager
import json
from datetime import datetime


class LotteryAnalyzer:
    """澳洲幸运5 规律分析器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.df = None
        self.patterns = {}
    
    def load_data(self):
        """加载数据"""
        self.df = self.db.get_all_data()
        if self.df.empty:
            logger.warning("没有可用数据")
            return False
        
        # 解析号码
        self.df['numbers_list'] = self.df['numbers'].apply(lambda x: [int(n) for n in x.split(',')])
        
        # 按时间正序排列（最旧的在前）- 与回测系统保持一致
        # 这样 tail(window) 才能获取最新的 window 期数据
        self.df = self.df.sort_values('draw_time', ascending=True).reset_index(drop=True)
        
        # 🔴 关键验证：确保数据顺序正确
        if len(self.df) > 1:
            assert self.df.iloc[0]['draw_time'] < self.df.iloc[-1]['draw_time'], \
                "数据必须按时间正序排列（旧→新）"
            logger.info(f"已加载 {len(self.df)} 条数据（按时间正序排列）")
            logger.info(f"  最旧: {self.df.iloc[0]['period_id']} ({self.df.iloc[0]['draw_time']})")
            logger.info(f"  最新: {self.df.iloc[-1]['period_id']} ({self.df.iloc[-1]['draw_time']})")
        
        return True
    
    def analyze_frequency(self, window: int = 100) -> dict:
        """频率分析"""
        # 使用 tail(window) 获取最新的 window 期数据（因为数据已按时间正序排列）
        recent_df = self.df.tail(window)
        all_numbers = []
        
        for numbers in recent_df['numbers_list']:
            all_numbers.extend(numbers)
        
        frequency = {}
        for i in range(10):
            count = all_numbers.count(i)
            frequency[i] = {
                "count": count,
                "frequency": count / len(all_numbers) if all_numbers else 0
            }
        
        # 排序
        hot_numbers = sorted(frequency.items(), key=lambda x: x[1]['frequency'], reverse=True)[:3]
        cold_numbers = sorted(frequency.items(), key=lambda x: x[1]['frequency'])[:3]
        
        return {
            "hot_numbers": [num[0] for num in hot_numbers],
            "cold_numbers": [num[0] for num in cold_numbers],
            "frequency_dict": frequency
        }
    
    def analyze_distribution(self, window: int = 100) -> dict:
        """分布分析"""
        # 使用 tail(window) 获取最新的 window 期数据
        recent_df = self.df.tail(window)
        
        odd_even_dist = {"3:2": 0, "2:3": 0, "4:1": 0, "1:4": 0, "5:0": 0, "0:5": 0}
        sum_dist = {"0-15": 0, "16-30": 0, "31-45": 0}
        
        for numbers in recent_df['numbers_list']:
            # 单双分析
            odd_count = sum(1 for n in numbers if n % 2 == 1)
            even_count = 5 - odd_count
            ratio = f"{odd_count}:{even_count}"
            if ratio in odd_even_dist:
                odd_even_dist[ratio] += 1
            
            # 和值分析
            total = sum(numbers)
            if total <= 15:
                sum_dist["0-15"] += 1
            elif total <= 30:
                sum_dist["16-30"] += 1
            else:
                sum_dist["31-45"] += 1
        
        # 转换为百分比
        total = len(recent_df)
        odd_even_dist = {k: v/total for k, v in odd_even_dist.items()}
        sum_dist = {k: v/total for k, v in sum_dist.items()}
        
        return {
            "odd_even_ratio": odd_even_dist,
            "sum_range": sum_dist
        }
    
    def analyze_long_dragon(self, window: int = 100) -> dict:
        """长龙分析"""
        # 使用 tail(window) 获取最新的 window 期数据
        recent_df = self.df.tail(window)
        
        max_odd_streak = 0
        max_even_streak = 0
        current_odd_streak = 0
        current_even_streak = 0
        
        for numbers in recent_df['numbers_list']:
            odd_count = sum(1 for n in numbers if n % 2 == 1)
            
            if odd_count >= 3:  # 单数占多数
                current_odd_streak += 1
                max_odd_streak = max(max_odd_streak, current_odd_streak)
                current_even_streak = 0
            else:
                current_even_streak += 1
                max_even_streak = max(max_even_streak, current_even_streak)
                current_odd_streak = 0
        
        return {
            "max_odd_streak": max_odd_streak,
            "max_even_streak": max_even_streak
        }
    
    def statistical_test(self, window: int = 100) -> dict:
        """统计检验"""
        # 使用 tail(window) 获取最新的 window 期数据
        recent_df = self.df.tail(window)
        all_numbers = []
        
        for numbers in recent_df['numbers_list']:
            all_numbers.extend(numbers)
        
        # 卡方检验
        observed = [all_numbers.count(i) for i in range(10)]
        expected = [len(all_numbers) / 10] * 10
        chi2, p_value = stats.chisquare(observed, expected)
        
        return {
            "chi_square": float(chi2),
            "p_value": float(p_value),
            "is_random": bool(p_value > 0.05),
            "significance": "★★" if p_value < 0.01 else ("★" if p_value < 0.05 else "")
        }
    
    def analyze(self, window: int = 100) -> dict:
        """完整分析"""
        if not self.load_data():
            return {}
        
        logger.info(f"开始分析（窗口大小: {window}）")
        
        self.patterns = {
            "period_range": f"{self.df.iloc[0]['period_id']}-{self.df.iloc[-1]['period_id']}",
            "total_periods": len(self.df),
            "last_update": datetime.now().isoformat(),
            "standard_patterns": {
                "frequency": self.analyze_frequency(window),
                "distribution": self.analyze_distribution(window),
                "long_dragon": self.analyze_long_dragon(window),
                "statistical_test": self.statistical_test(window)
            }
        }
        
        logger.info("分析完成")
        return self.patterns
    
    def save_patterns(self, output_path: str = "data/summary.json"):
        """保存分析结果"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到 {output_path}")
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")


def main():
    """主函数"""
    analyzer = LotteryAnalyzer()
    patterns = analyzer.analyze(window=100)
    analyzer.save_patterns()


if __name__ == "__main__":
    main()
