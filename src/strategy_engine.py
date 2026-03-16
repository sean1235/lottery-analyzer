"""投注策略引擎 - 处理复杂的多期策略和风控"""
import pandas as pd
from loguru import logger
from utils import DatabaseManager
from typing import Dict, List, Tuple


class StrategyEngine:
    """投注策略引擎"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.df = None
        
        # 初始本金
        self.capital_original = 2000  # 原核心算法本金
        self.capital_dual = 2000      # 双锚定算法本金
        
        # 风控底线
        self.min_capital = 1000
        self.resume_capital = 1200
        
        # 基础下注单位
        self.base_bet = 300  # 1仓 = 300积分
        
        # 赔率参数
        self.win_rate = 1/3 * (1 - 0.03)  # 0.3233
        
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
        
        # 按时间排序（最旧的在前，用于回测）
        # 这样 idx+1 才是真正的"下一期"
        self.df = self.df.sort_values('draw_time', ascending=True).reset_index(drop=True)
        
        # 🔴 关键验证：确保数据顺序正确
        if len(self.df) > 1:
            assert self.df.iloc[0]['draw_time'] < self.df.iloc[-1]['draw_time'], \
                "数据必须按时间正序排列（旧→新）"
            logger.info(f"已加载 {len(self.df)} 条数据（按时间正序排列）")
            logger.info(f"  最旧: {self.df.iloc[0]['period_id']} ({self.df.iloc[0]['draw_time']})")
            logger.info(f"  最新: {self.df.iloc[-1]['period_id']} ({self.df.iloc[-1]['draw_time']})")
        
        return True
    
    def calculate_exclusion_original(self, numbers: List[int]) -> int:
        """
        原核心算法：计算当期排除值
        N期开奖号和值 ÷ 4 取余数 = N+1期当期排除值
        """
        sum_value = sum(numbers)
        return sum_value % 4
    
    def calculate_exclusion_dual(self, numbers: List[int]) -> int:
        """
        双锚定算法：计算当期排除值
        S = (d1+d5) + (d2+d4)
        D = |d5-d4|
        (S+D) ÷ 4 取余数 = N+1期当期排除值
        """
        d1, d2, d3, d4, d5 = numbers
        S = (d1 + d5) + (d2 + d4)
        D = abs(d5 - d4)
        return (S + D) % 4
    
    def check_prediction(self, exclusion_value: int, next_numbers: List[int]) -> bool:
        """
        判定预测是否正确
        N+1期开奖号后两位 ÷ 4 取余数 ≠ 当期排除值 → 正确
        """
        last_two = next_numbers[-2] * 10 + next_numbers[-1]
        actual_value = last_two % 4
        return actual_value != exclusion_value
    
    def analyze_recent_performance(self, start_idx: int, window: int = 10) -> Dict:
        """
        分析最近N期的表现
        返回：正确率、最长连对、最长连错等
        """
        if start_idx + window >= len(self.df):
            return None
        
        results = []
        for i in range(start_idx, start_idx + window):
            if i + 1 >= len(self.df):
                break
            
            current_numbers = self.df.iloc[i]['numbers_list']
            next_numbers = self.df.iloc[i + 1]['numbers_list']
            
            # 双锚定算法预测
            exclusion = self.calculate_exclusion_dual(current_numbers)
            is_correct = self.check_prediction(exclusion, next_numbers)
            results.append(is_correct)
        
        if not results:
            return None
        
        # 计算统计指标
        correct_count = sum(results)
        accuracy = correct_count / len(results)
        
        # 最长连对
        max_streak = 0
        current_streak = 0
        for r in results:
            if r:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        # 最长连错
        max_error_streak = 0
        current_error_streak = 0
        for r in results:
            if not r:
                current_error_streak += 1
                max_error_streak = max(max_error_streak, current_error_streak)
            else:
                current_error_streak = 0
        
        return {
            'accuracy': accuracy,
            'correct_count': correct_count,
            'total_count': len(results),
            'max_streak': max_streak,
            'max_error_streak': max_error_streak,
            'results': results
        }
    
    def determine_market_level(self, idx: int) -> str:
        """
        判定盘面等级（基于双锚定算法）
        返回：黄金盈利期、稳定盈利期、观察期、混乱期
        """
        # 检查前6期
        recent_6 = self.analyze_recent_performance(idx, window=6)
        if not recent_6:
            return "数据不足"
        
        # 检查近10期
        recent_10 = self.analyze_recent_performance(idx, window=10)
        if not recent_10:
            return "数据不足"
        
        # 混乱期判定（最高优先级）
        # 前6期出现连续错误≥2期
        if recent_6['max_error_streak'] >= 2:
            return "混乱期"
        
        # 前6期出现对错交替
        has_alternation = False
        for i in range(len(recent_6['results']) - 1):
            if recent_6['results'][i] != recent_6['results'][i + 1]:
                has_alternation = True
                break
        
        if has_alternation:
            return "混乱期"
        
        # 黄金盈利期判定
        if (recent_6['accuracy'] == 1.0 and 
            recent_10['accuracy'] == 1.0 and 
            recent_10['max_streak'] >= 6 and 
            recent_10['max_error_streak'] <= 1):
            return "黄金盈利期"
        
        # 稳定盈利期判定
        if (recent_6['accuracy'] == 1.0 and 
            recent_10['accuracy'] >= 0.9 and 
            recent_10['max_streak'] >= 3 and 
            recent_10['max_error_streak'] <= 1):
            return "稳定盈利期"
        
        # 观察期
        if (recent_6['max_error_streak'] < 2 and 
            recent_10['accuracy'] >= 0.4):
            return "观察期"
        
        return "混乱期"
    
    def calculate_bet_size(self, market_level: str, streak_count: int) -> float:
        """
        根据盘面等级和连对次数计算下注仓位
        返回：下注金额（积分）
        """
        if market_level == "黄金盈利期":
            if 1 <= streak_count <= 5:
                return self.base_bet * 1.0  # 1仓
            elif streak_count >= 6:
                return self.base_bet * 0.5  # 0.5仓（后期降仓）
        
        elif market_level == "稳定盈利期":
            if 1 <= streak_count <= 3:
                return self.base_bet * 0.5  # 0.5仓
            elif streak_count >= 4:
                return self.base_bet * 0.3  # 0.3仓（后期降仓）
        
        # 观察期、混乱期、其他情况
        return 0.0
    
    def generate_strategy_report(self, periods: int = 20) -> pd.DataFrame:
        """
        生成策略分析报告
        """
        if not self.load_data():
            return pd.DataFrame()
        
        report_data = []
        
        for idx in range(min(periods, len(self.df) - 1)):
            period_id = self.df.iloc[idx]['period_id']
            current_numbers = self.df.iloc[idx]['numbers_list']
            next_numbers = self.df.iloc[idx + 1]['numbers_list']
            
            # 计算排除值
            y_original = self.calculate_exclusion_original(current_numbers)
            y_dual = self.calculate_exclusion_dual(current_numbers)
            
            # 判定结果
            is_correct_original = self.check_prediction(y_original, next_numbers)
            is_correct_dual = self.check_prediction(y_dual, next_numbers)
            
            # 判定盘面等级
            market_level = self.determine_market_level(idx)
            
            # 分析近期表现
            performance = self.analyze_recent_performance(idx, window=10)
            max_streak = performance['max_streak'] if performance else 0
            accuracy = performance['accuracy'] if performance else 0
            
            # 判定是否可以参与
            can_participate = False
            reason = ""
            bet_size = 0.0
            
            # 优先级1：混乱期禁止
            if market_level == "混乱期":
                reason = "触发混乱期红线，强制禁止"
            
            # 优先级2：上期错误空仓
            elif idx > 0:
                prev_dual_correct = self.check_prediction(
                    self.calculate_exclusion_dual(self.df.iloc[idx - 1]['numbers_list']),
                    current_numbers
                )
                if not prev_dual_correct:
                    reason = "上期判定错误，单独空仓"
            
            # 优先级3：Y原≠Y双 且处于盈利期
            elif y_original != y_dual and market_level in ["黄金盈利期", "稳定盈利期"]:
                can_participate = True
                bet_size = self.calculate_bet_size(market_level, max_streak)
                reason = f"可参与（Y原≠Y双，{market_level}）"
            
            # 优先级4：连续Y原=Y双 且双锚定连续正确
            elif y_original == y_dual and market_level in ["黄金盈利期", "稳定盈利期"]:
                # 检查是否连续2期Y原=Y双
                if idx >= 1:
                    prev_y_original = self.calculate_exclusion_original(self.df.iloc[idx - 1]['numbers_list'])
                    prev_y_dual = self.calculate_exclusion_dual(self.df.iloc[idx - 1]['numbers_list'])
                    if prev_y_original == prev_y_dual:
                        can_participate = True
                        bet_size = self.calculate_bet_size(market_level, max_streak)
                        reason = f"可参与（连续Y原=Y双，{market_level}）"
                    else:
                        reason = "Y原=Y双但未连续2期，空仓"
                else:
                    reason = "Y原=Y双但未连续2期，空仓"
            
            else:
                reason = "不满足参与条件，空仓"
            
            # 计算盈亏
            profit_loss = 0.0
            if can_participate and bet_size > 0:
                if is_correct_dual:
                    profit_loss = bet_size * self.win_rate
                else:
                    profit_loss = -bet_size
            
            report_data.append({
                '期号': period_id,
                '开奖号码': ' '.join(map(str, current_numbers)),
                'Y原': y_original,
                'Y双': y_dual,
                '原算法结果': '✓' if is_correct_original else '✗',
                '双锚定结果': '✓' if is_correct_dual else '✗',
                '盘面等级': market_level,
                '近10期正确率': f"{accuracy:.0%}" if performance else "N/A",
                '最长连对': max_streak,
                '操作建议': reason,
                '下注金额': f"{bet_size:.0f}" if bet_size > 0 else "0",
                '盈亏': f"{profit_loss:+.2f}" if profit_loss != 0 else "0"
            })
        
        return pd.DataFrame(report_data)


def main():
    """测试函数"""
    engine = StrategyEngine()
    
    print("\n" + "="*80)
    print("投注策略分析报告")
    print("="*80)
    
    report = engine.generate_strategy_report(periods=20)
    
    if not report.empty:
        print(report.to_string(index=False))
        
        # 统计总盈亏
        total_profit = report['盈亏'].apply(lambda x: float(x) if x != '0' else 0.0).sum()
        print("\n" + "="*80)
        print(f"总盈亏: {total_profit:+.2f} 积分")
        print("="*80)
    else:
        print("无数据")


if __name__ == "__main__":
    main()
