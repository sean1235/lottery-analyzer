"""策略回测引擎 - 执行自定义策略并生成回测报告"""
import pandas as pd
from loguru import logger
from utils import DatabaseManager
from typing import Dict, Any, Callable
import traceback


class StrategyBacktester:
    """策略回测引擎"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.df = None
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
    
    def execute_strategy(self, strategy_code: str, periods: int = None) -> pd.DataFrame:
        """
        执行策略回测
        
        Args:
            strategy_code: 策略函数代码
            periods: 回测期数，None表示回测所有数据
        
        Returns:
            DataFrame: 回测结果
        """
        if not self.load_data():
            return pd.DataFrame()
        
        # 编译策略代码
        try:
            namespace = {}
            exec(strategy_code, namespace)
            strategy_func = namespace.get('custom_strategy')
            
            if not strategy_func:
                logger.error("策略代码中未找到 custom_strategy 函数")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"策略代码编译失败: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
        
        # 执行回测
        results = []
        
        # 🟢 第一遍：计算所有期的预测值和验证结果
        predictions = []
        for idx in range(len(self.df) - 1):
            current_numbers = self.df.iloc[idx]['numbers_list']
            next_numbers = self.df.iloc[idx + 1]['numbers_list']
            
            # 计算排除值（使用双锚定算法）
            d1, d2, d3, d4, d5 = current_numbers
            S = (d1 + d5) + (d2 + d4)
            D = abs(d5 - d4)
            exclusion = (S + D) % 4
            
            # 验证预测
            last_two = next_numbers[-2] * 10 + next_numbers[-1]
            is_correct = (last_two % 4) != exclusion
            
            predictions.append({
                'period_id': self.df.iloc[idx]['period_id'],
                'numbers_list': current_numbers,
                'draw_time': self.df.iloc[idx]['draw_time'],
                'prediction': exclusion,
                'is_correct': is_correct
            })
        
        # 🟢 第二遍：执行策略决策
        # 如果periods为None，回测所有数据（包括最后一期）
        max_periods = len(self.df) if periods is None else min(periods, len(self.df))
        for idx in range(max_periods):
            try:
                period_id = self.df.iloc[idx]['period_id']
                current_numbers = self.df.iloc[idx]['numbers_list']
                
                # 准备历史数据（包含预测验证结果）
                history = []
                start_idx = max(0, idx - 19)
                for i in range(start_idx, idx + 1):
                    if i < len(predictions):
                        history.append(predictions[i])
                    else:
                        history.append({
                            'period_id': self.df.iloc[i]['period_id'],
                            'numbers_list': self.df.iloc[i]['numbers_list'],
                            'draw_time': self.df.iloc[i]['draw_time']
                        })
                
                # 反转：使 history[0] 成为当期
                history = list(reversed(history))
                
                # 🔴 关键：策略函数只接收 current_numbers 和 history
                # 不传递 next_numbers，完全模拟实盘环境
                result = strategy_func(current_numbers, history, idx)
                
                # 🟢 回测引擎负责验证预测结果
                prediction = result.get('prediction')
                is_correct = predictions[idx]['is_correct'] if idx < len(predictions) else False
                
                # 计算盈亏
                profit_loss = 0.0
                if result.get('can_participate') and result.get('bet_size', 0) > 0:
                    bet_size = result['bet_size']
                    
                    if is_correct:
                        profit_loss = bet_size * self.win_rate
                    else:
                        profit_loss = -bet_size
                
                results.append({
                    '期号': period_id,
                    '开奖号码': ' '.join(map(str, current_numbers)),
                    '预测值': result.get('prediction', 'N/A'),
                    '预测结果': '✓' if is_correct else '✗',
                    '是否参与': '是' if result.get('can_participate') else '否',
                    '下注金额': f"{result.get('bet_size', 0):.0f}",
                    '盈亏': f"{profit_loss:+.2f}" if profit_loss != 0 else "0",
                    '操作原因': result.get('reason', '')
                })
            
            except Exception as e:
                logger.error(f"执行策略失败（期号 {period_id}）: {e}")
                logger.error(traceback.format_exc())
                results.append({
                    '期号': period_id,
                    '开奖号码': ' '.join(map(str, current_numbers)),
                    '预测值': 'ERROR',
                    '预测结果': '✗',
                    '是否参与': '否',
                    '下注金额': '0',
                    '盈亏': '0',
                    '操作原因': f'策略执行错误: {str(e)}'
                })
        
        return pd.DataFrame(results)
    
    def generate_summary(self, results: pd.DataFrame) -> Dict[str, Any]:
        """生成回测摘要"""
        if results.empty:
            return {}
        
        total_periods = len(results)
        participated = len(results[results['是否参与'] == '是'])
        
        # 计算盈亏 - 将字符串转换为浮点数
        # 盈亏列格式: "+97.00", "-300.00", "0"
        def parse_profit(x):
            try:
                return float(x)
            except (ValueError, TypeError):
                return 0.0
        
        results['盈亏_数值'] = results['盈亏'].apply(parse_profit)
        total_profit = results['盈亏_数值'].sum()
        
        # 计算胜率（仅统计参与的期数）
        win_count = len(results[
            (results['是否参与'] == '是') & 
            (results['预测结果'] == '✓')
        ])
        loss_count = len(results[
            (results['是否参与'] == '是') & 
            (results['预测结果'] == '✗')
        ])
        win_rate = win_count / participated if participated > 0 else 0
        
        # 计算整体预测准确率（包括未参与的期数）
        total_correct = len(results[results['预测结果'] == '✓'])
        overall_accuracy = total_correct / total_periods if total_periods > 0 else 0
        
        # 计算最大回撤
        results['累计盈亏'] = results['盈亏_数值'].cumsum()
        max_drawdown = 0
        peak = 0
        for value in results['累计盈亏']:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_periods': total_periods,
            'participated': participated,
            'participation_rate': participated / total_periods if total_periods > 0 else 0,
            'total_profit': total_profit,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'overall_accuracy': overall_accuracy,
            'max_drawdown': max_drawdown,
            'avg_profit_per_bet': total_profit / participated if participated > 0 else 0
        }


def main():
    """测试函数"""
    backtester = StrategyBacktester()
    
    # 简单的测试策略
    test_code = """
def custom_strategy(current_numbers, history, idx):
    # 计算排除值
    exclusion = sum(current_numbers) % 4
    
    # 简单策略：总是参与，下注300
    return {
        'can_participate': True,
        'bet_size': 300,
        'reason': '测试策略',
        'prediction': exclusion
    }
"""
    
    print("\n" + "="*60)
    print("策略回测测试")
    print("="*60)
    
    results = backtester.execute_strategy(test_code, periods=10)
    
    if not results.empty:
        print("\n回测结果:")
        print(results.to_string(index=False))
        
        summary = backtester.generate_summary(results)
        print("\n" + "="*60)
        print("回测摘要:")
        print(f"总期数: {summary['total_periods']}")
        print(f"参与期数: {summary['participated']}")
        print(f"参与率: {summary['participation_rate']:.1%}")
        print(f"总盈亏: {summary['total_profit']:+.2f}")
        print(f"胜率: {summary['win_rate']:.1%}")
        print(f"最大回撤: {summary['max_drawdown']:.2f}")
        print("="*60)


if __name__ == "__main__":
    main()
