"""AI 规则解析器 - 使用 LLM 将自然语言转换为规则条件"""
from loguru import logger
import json
import os


class AIRuleParser:
    """AI 驱动的规则解析器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.system_prompt = """你是一个彩票规则解析专家。你的任务是将用户的自然语言描述转换为可执行的条件表达式。

可用的变量：
- sum: 5个号码的总和 (范围: 0-45)
- odd_count: 单数(奇数)的个数 (范围: 0-5)
- even_count: 双数(偶数)的个数 (范围: 0-5)
- big_count: 大号(5-9)的个数 (范围: 0-5)
- small_count: 小号(0-4)的个数 (范围: 0-5)
- has_duplicate: 是否有重复号码 (True/False)
- has_sequence: 最长连续号码的长度 (范围: 1-5)

运算符：
- 比较: >, <, >=, <=, ==, !=
- 逻辑: AND, OR, NOT

示例转换：
1. "和值大于25并且单数至少3个" → "sum > 25 AND odd_count >= 3"
2. "出现3个以上大号且没有重复" → "big_count > 3 AND NOT has_duplicate"
3. "单数占多数或者和值超过30" → "odd_count >= 3 OR sum > 30"
4. "和值在20到30之间" → "sum >= 20 AND sum <= 30"
5. "没有重复且有连号" → "NOT has_duplicate AND has_sequence >= 2"
6. "全是单数" → "odd_count == 5"
7. "大小号各一半" → "big_count >= 2 AND big_count <= 3"
8. "单双平衡" → "odd_count >= 2 AND odd_count <= 3"
9. "和值偏大且大号多" → "sum > 25 AND big_count >= 3"
10. "冷门组合：小号多且和值低" → "small_count >= 4 AND sum < 15"

请将用户输入转换为条件表达式，并以 JSON 格式返回：
{
    "condition": "转换后的条件表达式",
    "explanation": "对规则的解释说明",
    "confidence": 0.95,
    "variables_used": ["sum", "odd_count"]
}

如果无法理解用户输入，返回：
{
    "condition": "",
    "explanation": "无法理解的原因",
    "confidence": 0.0,
    "error": "错误描述"
}

重要：只返回 JSON，不要有其他文字。"""
    
    def parse(self, natural_text: str, use_ai: bool = True) -> dict:
        """
        解析自然语言规则
        
        Args:
            natural_text: 自然语言描述
            use_ai: 是否使用 AI 解析（如果为 False，使用简单的模式匹配）
        
        Returns:
            dict: {
                'condition': 条件表达式,
                'explanation': 规则解释,
                'confidence': 解析置信度 (0-1),
                'variables_used': 使用的变量列表
            }
        """
        if not natural_text or not natural_text.strip():
            return {
                'condition': '',
                'explanation': '输入为空',
                'confidence': 0.0,
                'error': '请输入规则描述'
            }
        
        if use_ai:
            return self._parse_with_ai(natural_text)
        else:
            return self._parse_with_patterns(natural_text)
    
    def _parse_with_ai(self, natural_text: str) -> dict:
        """使用 AI 解析（OpenAI API）"""
        try:
            if not self.api_key:
                logger.warning("未配置 OpenAI API Key，使用模式匹配")
                return self._parse_with_patterns(natural_text)
            
            # 导入 OpenAI
            try:
                from openai import OpenAI
            except ImportError:
                logger.error("未安装 openai 库，请运行: pip install openai")
                return self._parse_with_patterns(natural_text)
            
            # 初始化客户端
            client = OpenAI(api_key=self.api_key)
            
            # 构建提示词
            user_prompt = f"请将以下自然语言规则转换为条件表达式：\n\n{natural_text}"
            
            logger.info(f"使用 AI 解析规则: {natural_text}")
            
            # 调用 OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # 解析响应
            content = response.choices[0].message.content.strip()
            logger.info(f"AI 响应: {content}")
            
            # 尝试解析 JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # 如果不是 JSON，尝试提取条件表达式
                logger.warning("AI 响应不是有效的 JSON，尝试提取内容")
                return {
                    'condition': content,
                    'explanation': 'AI 生成的条件',
                    'confidence': 0.7,
                    'method': 'ai_raw'
                }
        
        except Exception as e:
            logger.error(f"AI 解析失败: {e}")
            # 降级到模式匹配
            logger.info("降级使用模式匹配")
            return self._parse_with_patterns(natural_text)
    
    def _parse_with_patterns(self, natural_text: str) -> dict:
        """使用模式匹配解析（简单版本）"""
        import re
        
        text = natural_text.strip()
        conditions = []
        variables_used = set()
        
        # 模式匹配规则
        patterns = [
            # 和值相关
            (r'和值\s*(大于|超过|高于)\s*(\d+)', lambda m: (f"sum > {m.group(2)}", ['sum'])),
            (r'和值\s*(小于|低于|少于)\s*(\d+)', lambda m: (f"sum < {m.group(2)}", ['sum'])),
            (r'和值\s*(至少|不少于)\s*(\d+)', lambda m: (f"sum >= {m.group(2)}", ['sum'])),
            (r'和值\s*在\s*(\d+)\s*到\s*(\d+)', lambda m: (f"sum >= {m.group(1)} AND sum <= {m.group(2)}", ['sum'])),
            
            # 单双相关
            (r'单数\s*(至少|不少于)\s*(\d+)', lambda m: (f"odd_count >= {m.group(2)}", ['odd_count'])),
            (r'单数\s*占多数', lambda m: ("odd_count >= 3", ['odd_count'])),
            (r'双数\s*(至少|不少于)\s*(\d+)', lambda m: (f"even_count >= {m.group(2)}", ['even_count'])),
            (r'双数\s*占多数', lambda m: ("even_count >= 3", ['even_count'])),
            (r'全是单数', lambda m: ("odd_count == 5", ['odd_count'])),
            (r'全是双数', lambda m: ("even_count == 5", ['even_count'])),
            
            # 大小相关
            (r'大号\s*(至少|不少于|超过)\s*(\d+)', lambda m: (f"big_count >= {m.group(2)}", ['big_count'])),
            (r'小号\s*(至少|不少于|超过)\s*(\d+)', lambda m: (f"small_count >= {m.group(2)}", ['small_count'])),
            (r'(\d+)\s*个以上\s*大号', lambda m: (f"big_count > {m.group(1)}", ['big_count'])),
            (r'(\d+)\s*个以上\s*小号', lambda m: (f"small_count > {m.group(1)}", ['small_count'])),
            
            # 重复和连号
            (r'(有|出现)\s*重复', lambda m: ("has_duplicate", ['has_duplicate'])),
            (r'(没有|无)\s*重复', lambda m: ("NOT has_duplicate", ['has_duplicate'])),
            (r'(有|出现)\s*连号', lambda m: ("has_sequence >= 2", ['has_sequence'])),
            (r'连号\s*长度\s*(大于|超过)\s*(\d+)', lambda m: (f"has_sequence > {m.group(2)}", ['has_sequence'])),
        ]
        
        # 尝试匹配所有模式
        for pattern, handler in patterns:
            match = re.search(pattern, text)
            if match:
                condition, vars_list = handler(match)
                conditions.append(condition)
                variables_used.update(vars_list)
        
        # 处理逻辑连接词
        if '并且' in text or '而且' in text or '同时' in text:
            logic_op = ' AND '
        elif '或者' in text or '或' in text:
            logic_op = ' OR '
        else:
            logic_op = ' AND '
        
        if not conditions:
            return {
                'condition': '',
                'explanation': '无法识别规则，请使用更明确的描述',
                'confidence': 0.0,
                'error': '未匹配到任何规则模式',
                'suggestions': self.get_examples()
            }
        
        final_condition = logic_op.join(conditions)
        
        return {
            'condition': final_condition,
            'explanation': f'解析为: {final_condition}',
            'confidence': 0.8,
            'variables_used': list(variables_used),
            'method': 'pattern_matching'
        }
    
    def get_examples(self) -> list:
        """获取示例规则"""
        return [
            "和值大于25并且单数至少3个",
            "出现3个以上大号且没有重复",
            "单数占多数或者和值超过30",
            "双数至少4个",
            "和值在20到30之间",
            "有连号且大号超过2个",
            "没有重复",
            "全是单数",
            "大小号各一半",
            "和值小于15并且小号至少3个"
        ]
    
    def get_prompt_for_user(self) -> str:
        """获取给用户的提示信息"""
        return """
💡 规则描述提示：

支持的描述方式：
1. 和值条件：
   - "和值大于25"
   - "和值在20到30之间"
   - "和值小于15"

2. 单双条件：
   - "单数至少3个"
   - "单数占多数"
   - "全是单数"
   - "双数至少4个"

3. 大小条件：
   - "大号超过3个"
   - "小号至少2个"
   - "3个以上大号"

4. 特殊条件：
   - "有重复" / "没有重复"
   - "有连号"
   - "连号长度大于2"

5. 组合条件：
   - 用"并且"、"而且"、"同时"连接多个条件（AND）
   - 用"或者"、"或"连接多个条件（OR）

示例：
- "和值大于25并且单数至少3个"
- "出现3个以上大号且没有重复"
- "单数占多数或者和值超过30"
"""


def main():
    """测试函数"""
    parser = AIRuleParser()
    
    print("\n" + "="*60)
    print("AI 规则解析器测试")
    print("="*60)
    
    # 测试示例
    examples = [
        "和值大于25并且单数至少3个",
        "出现3个以上大号且没有重复",
        "单数占多数或者和值超过30",
        "双数至少4个",
        "和值在20到30之间",
        "有连号且大号超过2个",
        "没有重复",
        "全是单数",
    ]
    
    for text in examples:
        print(f"\n输入: {text}")
        result = parser.parse(text, use_ai=False)  # 使用模式匹配
        print(f"条件: {result.get('condition', 'N/A')}")
        print(f"解释: {result.get('explanation', 'N/A')}")
        print(f"置信度: {result.get('confidence', 0):.2f}")
        if 'error' in result:
            print(f"错误: {result['error']}")
        print("-" * 60)


if __name__ == "__main__":
    main()
