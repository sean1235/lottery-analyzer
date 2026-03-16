"""自定义策略解析器 - 将自然语言转换为可执行的策略代码"""
from loguru import logger
import json
import os
from typing import Dict, Any


class CustomStrategyParser:
    """自定义策略解析器"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL')
        self.system_prompt = """你是一个彩票投注策略代码生成专家。你的任务是将用户的自然语言策略描述转换为可执行的 Python 代码。

## 🔴🔴🔴 最高优先级：完全遵循用户指示 🔴🔴🔴

### 铁律1：100% 遵循用户描述
- **必须逐条实现用户提到的每一个条件、规则、判断逻辑**
- **不得遗漏、简化、省略、合并任何用户明确提到的步骤**
- **不得添加用户没有要求的额外逻辑或"优化"**
- **不得用自己的理解替代用户的原始描述**
- **如果用户说"必须"、"只有当"、"仅在"，必须严格实现为代码中的 if 条件**

### 铁律2：优先级规则必须完整
- 用户描述的优先级规则必须按顺序全部实现
- 每个优先级的所有条件都必须检查
- 不得跳过任何优先级判断

### 铁律3：条件判断必须精确
- 用户提到的每个"且"、"或"、"不等于"都必须体现在代码中
- 用户提到的数值、阈值必须精确使用，不得修改
- 用户提到的算法公式必须完全一致

### 铁律4：验证生成的代码
- 生成代码后，必须自我检查是否遗漏了用户的任何要求
- 如果发现遗漏，必须补充完整

## 🔴 实盘模拟原则

策略函数必须完全模拟实盘环境：
- ✅ 可以使用：当期号码、历史数据
- ❌ 不能使用：下期号码（实盘时根本不知道）
- 策略只能基于已知信息做决策，回测引擎负责验证结果

## 可用的数据和方法：

### 当期数据（current_numbers: List[int]）
- 5个号码的列表，例如 [1, 3, 2, 4, 6]
- 索引：d1=numbers[0], d2=numbers[1], d3=numbers[2], d4=numbers[3], d5=numbers[4]

### 历史数据（history: List[Dict]）
- 每个元素包含：period_id, numbers_list, draw_time
- history[0] 是当期，history[1] 是上一期，以此类推
- 可以访问任意历史期数进行统计分析
- ⚠️ 注意：history 中已经包含了每期的预测结果验证

### 核心算法实现：

```python
# 1. 排除值计算
def calc_exclusion_original(numbers):
    '''原核心算法: 和值÷4取余数'''
    return sum(numbers) % 4

def calc_exclusion_dual(numbers):
    '''双锚定算法: (S+D)÷4取余数'''
    d1, d2, d3, d4, d5 = numbers
    S = (d1 + d5) + (d2 + d4)
    D = abs(d5 - d4)
    return (S + D) % 4

# 2. 分析近期表现（使用 history 中的验证结果）
def analyze_recent_performance(history, window):
    '''
    分析最近N期的表现
    参数:
        history: 历史数据列表（history[0]是当期）
        window: 分析窗口大小
    返回: 正确率、最长连对、最长连错、连续结果列表
    '''
    # 从 history[1] 开始（上一期），分析最近 window 期
    results = []
    for i in range(1, min(window + 1, len(history))):
        if 'is_correct' in history[i]:
            results.append(history[i]['is_correct'])
    
    if not results:
        return None
    
    # 计算统计指标
    accuracy = sum(results) / len(results)
    
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
        'max_streak': max_streak,
        'max_error_streak': max_error_streak,
        'results': results
    }
    
    if not results:
        return None
    
    # 计算统计指标
    accuracy = sum(results) / len(results)
    
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
        'max_streak': max_streak,
        'max_error_streak': max_error_streak,
        'results': results
    }

# 3. 判定盘面等级
def determine_market_level(history):
    '''
    判定盘面等级（基于双锚定算法）
    参数:
        history: 历史数据列表（history[0]是当期，history[1]是上一期）
    返回: 黄金盈利期、稳定盈利期、观察期、混乱期
    '''
    # 检查前6期
    recent_6 = analyze_recent_performance(history, 6)
    if not recent_6:
        return "数据不足"
    
    # 检查近10期
    recent_10 = analyze_recent_performance(history, 10)
    if not recent_10:
        return "数据不足"
    
    # 混乱期判定（最高优先级）
    if recent_6['max_error_streak'] >= 2:
        return "混乱期"
    
    # 检查对错交替
    has_alternation = False
    for i in range(len(recent_6['results']) - 1):
        if recent_6['results'][i] != recent_6['results'][i + 1]:
            has_alternation = True
            break
    
    if has_alternation:
        return "混乱期"
    
    # 黄金盈利期
    if (recent_6['accuracy'] == 1.0 and 
        recent_10['accuracy'] == 1.0 and 
        recent_10['max_streak'] >= 6):
        return "黄金盈利期"
    
    # 稳定盈利期
    if (recent_6['accuracy'] == 1.0 and 
        recent_10['accuracy'] >= 0.9 and 
        recent_10['max_streak'] >= 3):
        return "稳定盈利期"
    
    # 观察期
    if recent_6['max_error_streak'] < 2 and recent_10['accuracy'] >= 0.4:
        return "观察期"
    
    return "混乱期"
```

## 策略实现要点：

1. **多期数据分析**: 使用 history 列表访问历史数据
2. **状态判定**: 实现盘面等级判定逻辑
3. **优先级规则**: 按优先级顺序判断是否参与
4. **仓位管理**: 根据盘面等级和连对次数动态调整
5. **风控机制**: 实现空仓、禁止参与等风控规则

## 输出格式：

返回 JSON 格式：
```json
{
    "strategy_name": "策略名称",
    "description": "策略描述",
    "code": "完整的 Python 函数代码（包含所有辅助函数）",
    "explanation": "代码逻辑说明"
}
```

## 代码模板：

```python
def custom_strategy(current_numbers, history, idx):
    '''
    自定义策略函数（完全模拟实盘环境）
    
    Args:
        current_numbers: 当期5个号码 [d1, d2, d3, d4, d5]
        history: 历史数据列表
            - history[0] 是当期（包含 period_id, numbers_list, draw_time, is_correct）
            - history[1] 是上一期（包含预测验证结果 is_correct）
            - history[i]['is_correct'] 表示该期的预测是否正确
        idx: 当前期在数据集中的索引
    
    Returns:
        dict: {
            'can_participate': bool,  # 是否参与
            'bet_size': float,  # 下注金额
            'reason': str,  # 操作原因
            'prediction': Any  # 预测值（排除值0-3）
        }
    '''
    
    # 1. 定义辅助函数（必须在函数内部定义）
    def calc_exclusion_dual(numbers):
        '''双锚定算法'''
        d1, d2, d3, d4, d5 = numbers
        S = (d1 + d5) + (d2 + d4)
        D = abs(d5 - d4)
        return (S + D) % 4
    
    def analyze_recent_performance(history, window):
        '''分析最近N期的表现'''
        results = []
        for i in range(1, min(window + 1, len(history))):
            if 'is_correct' in history[i]:
                results.append(history[i]['is_correct'])
        
        if not results:
            return None
        
        accuracy = sum(results) / len(results)
        
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
            'max_streak': max_streak,
            'max_error_streak': max_error_streak,
            'results': results
        }
    
    # 2. 计算当期排除值（预测）
    y_dual = calc_exclusion_dual(current_numbers)
    
    # 3. 分析历史数据，判定盘面等级
    recent_6 = analyze_recent_performance(history, 6)
    recent_10 = analyze_recent_performance(history, 10)
    
    # 判定盘面等级
    if not recent_6 or not recent_10:
        market_level = "数据不足"
    elif recent_6['max_error_streak'] >= 2:
        market_level = "混乱期"
    elif recent_6['accuracy'] == 1.0 and recent_10['accuracy'] == 1.0 and recent_10['max_streak'] >= 6:
        market_level = "黄金盈利期"
    elif recent_6['accuracy'] == 1.0 and recent_10['accuracy'] >= 0.9 and recent_10['max_streak'] >= 3:
        market_level = "稳定盈利期"
    else:
        market_level = "观察期"
    
    # 4. 根据优先级规则决定是否参与
    can_participate = False
    bet_size = 0
    reason = ""
    
    # 优先级1：混乱期禁止
    if market_level == "混乱期":
        reason = "混乱期，禁止参与"
    # 优先级2：上期错误空仓
    elif len(history) > 1 and 'is_correct' in history[1] and not history[1]['is_correct']:
        reason = "上期错误，空仓"
    # 优先级3：可参与条件判定
    elif market_level in ["黄金盈利期", "稳定盈利期"]:
        can_participate = True
        bet_size = 300 if market_level == "黄金盈利期" else 150
        reason = f"{market_level}，按仓位策略下注"
    else:
        reason = "不满足参与条件，空仓"
    
    return {
        'can_participate': can_participate,
        'bet_size': bet_size,
        'reason': reason,
        'prediction': y_dual
    }
```

## 重要提示：

1. 所有辅助函数必须在 custom_strategy 函数内部定义
2. 使用 history 列表进行多期数据分析
3. 严格按照优先级顺序判断规则
4. 实现完整的风控和仓位管理逻辑
5. 代码必须是完整可执行的，不要有省略或TODO
6. **🔴 最重要：逐条检查用户描述，确保每个条件都已实现**

请根据用户的自然语言描述生成完整的策略代码。

**生成前必须自问：**
- 用户提到的每个条件我都实现了吗？
- 用户提到的优先级规则我都按顺序检查了吗？
- 用户提到的算法公式我都正确实现了吗？
- 用户提到的"必须"、"只有当"我都转换成 if 条件了吗？

只返回 JSON，不要其他文字。
"""

    def parse_strategy(self, natural_text: str) -> Dict[str, Any]:
        """
        解析自然语言策略描述，生成可执行代码
        
        Args:
            natural_text: 自然语言策略描述
        
        Returns:
            dict: {
                'strategy_name': 策略名称,
                'description': 策略描述,
                'code': Python 代码,
                'explanation': 代码说明,
                'success': bool
            }
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': '未配置 OpenAI API Key'
                }
            
            # 导入 OpenAI
            try:
                from openai import OpenAI
            except ImportError:
                return {
                    'success': False,
                    'error': '未安装 openai 库'
                }
            
            # 初始化客户端
            if self.base_url:
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                client = OpenAI(api_key=self.api_key)
            
            logger.info(f"使用 AI 解析策略: {natural_text}")
            
            # 调用 OpenAI API
            response = client.chat.completions.create(
                model="gpt-4",  # 使用 GPT-4 以获得更好的代码生成质量
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"请将以下策略描述转换为 Python 代码：\n\n{natural_text}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # 调试：打印响应类型
            logger.info(f"响应类型: {type(response)}")
            logger.info(f"响应内容: {response}")
            
            # 解析响应
            if isinstance(response, str):
                # 如果返回的是字符串，直接使用
                content = response.strip()
            else:
                # 正常的 OpenAI 响应对象
                content = response.choices[0].message.content.strip()
            
            logger.info(f"AI 响应: {content[:200]}...")
            
            # 提取 JSON
            # 尝试找到 JSON 块
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            result = json.loads(content)
            result['success'] = True
            
            return result
        
        except Exception as e:
            logger.error(f"策略解析失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_code(self, code: str) -> bool:
        """验证生成的代码是否有效"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logger.error(f"代码语法错误: {e}")
            return False
    
    def get_example_strategies(self) -> list:
        """获取示例策略"""
        return [
            {
                'name': '双锚定排除值策略',
                'description': '使用双锚定算法计算排除值，前6期全部正确且近10期正确率100%时参与'
            },
            {
                'name': '和值区间策略',
                'description': '当和值在20-30之间，且单数至少3个时参与，下注1仓'
            },
            {
                'name': '连对降仓策略',
                'description': '连续正确1-5期时下注1仓，连续正确6期以上时降为0.5仓'
            },
            {
                'name': '上期错误空仓策略',
                'description': '如果上一期预测错误，本期强制空仓'
            }
        ]


def main():
    """测试函数"""
    parser = CustomStrategyParser(api_key="sk-DGSBXqgsXGVeyoU5LQyth3eQcEQFxFSRBgfaboOtVfd1gBTE")
    
    print("\n" + "="*60)
    print("自定义策略解析器测试")
    print("="*60)
    
    # 测试策略
    test_strategy = """
    使用双锚定算法计算排除值。
    如果前6期全部正确，且近10期正确率达到100%，最长连对大于等于6期，则判定为黄金盈利期。
    在黄金盈利期，如果连对1-5期，下注1仓（300积分）；如果连对6期以上，降为0.5仓（150积分）。
    如果上一期预测错误，本期强制空仓。
    """
    
    print(f"\n策略描述:\n{test_strategy}")
    print("\n正在解析...")
    
    result = parser.parse_strategy(test_strategy)
    
    if result.get('success'):
        print(f"\n策略名称: {result.get('strategy_name')}")
        print(f"\n策略说明: {result.get('explanation')}")
        print(f"\n生成的代码:\n{result.get('code')}")
    else:
        print(f"\n解析失败: {result.get('error')}")


if __name__ == "__main__":
    main()
