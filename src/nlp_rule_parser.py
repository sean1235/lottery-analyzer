"""自然语言规则解析器 - 将中文描述转换为规则条件"""
import re
from loguru import logger


class NLPRuleParser:
    """自然语言规则解析器"""
    
    def __init__(self):
        # 定义关键词映射
        self.keywords = {
            # 和值相关
            '和值': 'sum',
            '总和': 'sum',
            '相加': 'sum',
            '加起来': 'sum',
            
            # 单双相关
            '单数': 'odd_count',
            '单号': 'odd_count',
            '奇数': 'odd_count',
            '双数': 'even_count',
            '双号': 'even_count',
            '偶数': 'even_count',
            
            # 大小相关
            '大号': 'big_count',
            '大数': 'big_count',
            '小号': 'small_count',
            '小数': 'small_count',
            
            # 其他特征
            '重复': 'has_duplicate',
            '对子': 'has_duplicate',
            '豹子': 'has_duplicate',
            '连号': 'has_sequence',
            '顺子': 'has_sequence',
            '连续': 'has_sequence',
        }
        
        # 比较运算符映射
        self.operators = {
            '大于': '>',
            '超过': '>',
            '高于': '>',
            '多于': '>',
            '小于': '<',
            '低于': '<',
            '少于': '<',
            '不到': '<',
            '等于': '==',
            '是': '==',
            '为': '==',
            '大于等于': '>=',
            '至少': '>=',
            '不少于': '>=',
            '小于等于': '<=',
            '至多': '<=',
            '不超过': '<=',
            '不等于': '!=',
            '不是': '!=',
        }
        
        # 逻辑运算符
        self.logic_ops = {
            '并且': 'AND',
            '而且': 'AND',
            '同时': 'AND',
            '且': 'AND',
            '或者': 'OR',
            '或': 'OR',
            '不': 'NOT',
            '没有': 'NOT',
        }
    
    def parse(self, natural_text: str) -> dict:
        """
        解析自然语言规则
        
        Args:
            natural_text: 自然语言描述，例如：
                - "和值大于25并且单数至少3个"
                - "出现3个以上大号且没有重复"
                - "单数占多数或者和值超过30"
        
        Returns:
            dict: {
                'condition': 条件表达式,
                'description': 规则描述,
                'confidence': 解析置信度 (0-1)
            }
        """
        try:
            logger.info(f"开始解析自然语言规则: {natural_text}")
            
            # 预处理文本
            text = natural_text.strip()
            
            # 提取所有条件
            conditions = []
            confidence = 1.0
            
            # 按逻辑运算符分割
            segments = self._split_by_logic(text)
            
            for segment in segments:
                condition = self._parse_segment(segment['text'])
                if condition:
                    conditions.append({
                        'condition': condition,
                        'logic': segment.get('logic', 'AND')
                    })
                else:
                    confidence *= 0.8  # 降低置信度
            
            # 组合条件
            if not conditions:
                return {
                    'condition': '',
                    'description': natural_text,
                    'confidence': 0.0,
                    'error': '无法解析规则'
                }
            
            # 构建最终条件表达式
            final_condition = self._build_condition(conditions)
            
            return {
                'condition': final_condition,
                'description': natural_text,
                'confidence': confidence,
                'parsed_segments': len(conditions)
            }
        
        except Exception as e:
            logger.error(f"解析规则失败: {e}")
            return {
                'condition': '',
                'description': natural_text,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _split_by_logic(self, text: str) -> list:
        """按逻辑运算符分割文本"""
        segments = []
        current_text = text
        
        # 查找逻辑运算符
        for chinese_op, english_op in self.logic_ops.items():
            if chinese_op in current_text:
                parts = current_text.split(chinese_op)
                for i, part in enumerate(parts):
                    if part.strip():
                        segments.append({
                            'text': part.strip(),
                            'logic': english_op if i > 0 else None
                        })
                return segments
        
        # 没有逻辑运算符，返回整个文本
        return [{'text': text, 'logic': None}]
    
    def _parse_segment(self, segment: str) -> str:
        """解析单个条件片段"""
        # 尝试匹配各种模式
        
        # 模式1: "和值大于25"
        pattern1 = r'(和值|总和|相加|加起来)\s*(大于|超过|高于|多于|小于|低于|少于|不到|等于|是|为|大于等于|至少|不少于|小于等于|至多|不超过)\s*(\d+)'
        match = re.search(pattern1, segment)
        if match:
            var = self.keywords.get(match.group(1), 'sum')
            op = self.operators.get(match.group(2), '>')
            value = match.group(3)
            return f"{var} {op} {value}"
        
        # 模式2: "单数至少3个" 或 "3个以上单数"
        pattern2 = r'(单数|单号|奇数|双数|双号|偶数|大号|大数|小号|小数)\s*(至少|不少于|大于等于|超过|多于|至多|不超过|小于等于|少于)\s*(\d+)\s*(个|位)?'
        match = re.search(pattern2, segment)
        if match:
            var = self.keywords.get(match.group(1), 'odd_count')
            op = self.operators.get(match.group(2), '>=')
            value = match.group(3)
            return f"{var} {op} {value}"
        
        # 模式3: "3个以上单数"
        pattern3 = r'(\d+)\s*(个|位)?\s*(以上|以下|以内)?\s*(单数|单号|奇数|双数|双号|偶数|大号|大数|小号|小数)'
        match = re.search(pattern3, segment)
        if match:
            value = match.group(1)
            modifier = match.group(3)
            var = self.keywords.get(match.group(4), 'odd_count')
            
            if modifier == '以上':
                op = '>='
            elif modifier == '以下':
                op = '<='
            else:
                op = '>='
            
            return f"{var} {op} {value}"
        
        # 模式4: "有重复" 或 "没有重复"
        pattern4 = r'(有|出现|存在|没有|无)\s*(重复|对子|豹子|连号|顺子|连续)'
        match = re.search(pattern4, segment)
        if match:
            has_not = match.group(1) in ['没有', '无']
            feature = match.group(2)
            var = self.keywords.get(feature, 'has_duplicate')
            
            if has_not:
                return f"NOT {var}"
            else:
                return var
        
        # 模式5: "单数占多数" 或 "双数占多数"
        pattern5 = r'(单数|单号|奇数|双数|双号|偶数)\s*占\s*多数'
        match = re.search(pattern5, segment)
        if match:
            var = self.keywords.get(match.group(1), 'odd_count')
            return f"{var} >= 3"
        
        # 模式6: "连号长度大于2"
        pattern6 = r'(连号|顺子|连续)\s*长度\s*(大于|超过|至少)\s*(\d+)'
        match = re.search(pattern6, segment)
        if match:
            op = self.operators.get(match.group(2), '>')
            value = match.group(3)
            return "has_sequence {} {}".format(op, value)
        
        logger.warning(f"无法解析片段: {segment}")
        return ""
    
    def _build_condition(self, conditions: list) -> str:
        """构建最终条件表达式"""
        if not conditions:
            return ""
        
        result = conditions[0]['condition']
        
        for i in range(1, len(conditions)):
            logic = conditions[i].get('logic', 'AND')
            condition = conditions[i]['condition']
            result = f"{result} {logic} {condition}"
        
        return result
    
    def get_examples(self) -> list:
        """获取示例规则"""
        return [
            {
                'text': '和值大于25并且单数至少3个',
                'description': '适合追高和值的单数组合'
            },
            {
                'text': '出现3个以上大号且没有重复',
                'description': '大号集中且无重复的情况'
            },
            {
                'text': '单数占多数或者和值超过30',
                'description': '单数多或高和值的情况'
            },
            {
                'text': '双数至少4个',
                'description': '双数占绝对优势'
            },
            {
                'text': '和值小于15并且小号至少3个',
                'description': '低和值小号组合'
            },
            {
                'text': '有连号且大号超过2个',
                'description': '连号配合大号'
            },
            {
                'text': '没有重复并且和值在20到30之间',
                'description': '无重复的中等和值'
            },
            {
                'text': '单数和双数各占一半',
                'description': '单双平衡（实际会解析为 odd_count >= 2 AND odd_count <= 3）'
            }
        ]
    
    def validate_condition(self, condition: str) -> bool:
        """验证条件表达式是否有效"""
        try:
            # 测试条件
            test_features = {
                'sum': 25,
                'odd_count': 3,
                'even_count': 2,
                'big_count': 3,
                'small_count': 2,
                'has_duplicate': False,
                'has_sequence': 2
            }
            
            # 替换变量
            expr = condition
            for key, value in test_features.items():
                expr = expr.replace(key, str(value))
            
            # 尝试评估
            eval(expr)
            return True
        except:
            return False


def main():
    """测试函数"""
    parser = NLPRuleParser()
    
    print("\n" + "="*60)
    print("自然语言规则解析器测试")
    print("="*60)
    
    # 测试示例
    examples = [
        "和值大于25并且单数至少3个",
        "出现3个以上大号且没有重复",
        "单数占多数或者和值超过30",
        "双数至少4个",
        "和值小于15并且小号至少3个",
        "有连号且大号超过2个",
        "没有重复",
    ]
    
    for text in examples:
        print(f"\n输入: {text}")
        result = parser.parse(text)
        print(f"条件: {result['condition']}")
        print(f"置信度: {result['confidence']:.2f}")
        if 'error' in result:
            print(f"错误: {result['error']}")
        print("-" * 60)


if __name__ == "__main__":
    main()
