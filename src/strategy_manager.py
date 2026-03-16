"""策略管理器 - 保存和加载策略"""
import json
import os
from datetime import datetime
from loguru import logger
from typing import List, Dict, Any


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, storage_dir: str = "data/strategies"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_strategy(self, strategy: Dict[str, Any]) -> bool:
        """
        保存策略
        
        Args:
            strategy: 策略字典，包含 strategy_name, description, code, explanation
        
        Returns:
            bool: 是否保存成功
        """
        try:
            # 生成文件名（使用策略名称和时间戳）
            strategy_name = strategy.get('strategy_name', 'unnamed_strategy')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 清理文件名（移除特殊字符）
            safe_name = "".join(c for c in strategy_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            
            filename = f"{safe_name}_{timestamp}.json"
            filepath = os.path.join(self.storage_dir, filename)
            
            # 添加元数据
            strategy_data = {
                'strategy_name': strategy.get('strategy_name'),
                'description': strategy.get('description'),
                'code': strategy.get('code'),
                'explanation': strategy.get('explanation'),
                'created_at': datetime.now().isoformat(),
                'filename': filename
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(strategy_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"策略已保存: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"保存策略失败: {e}")
            return False
    
    def load_strategy(self, filename: str) -> Dict[str, Any]:
        """
        加载策略
        
        Args:
            filename: 策略文件名
        
        Returns:
            dict: 策略数据
        """
        try:
            filepath = os.path.join(self.storage_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                strategy_data = json.load(f)
            
            logger.info(f"策略已加载: {filepath}")
            return strategy_data
        
        except Exception as e:
            logger.error(f"加载策略失败: {e}")
            return {}
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        列出所有已保存的策略
        
        Returns:
            list: 策略列表
        """
        try:
            strategies = []
            
            # 遍历策略目录
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.storage_dir, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            strategy_data = json.load(f)
                        
                        strategies.append({
                            'filename': filename,
                            'strategy_name': strategy_data.get('strategy_name', 'Unknown'),
                            'description': strategy_data.get('description', ''),
                            'created_at': strategy_data.get('created_at', ''),
                            'file_size': os.path.getsize(filepath)
                        })
                    except Exception as e:
                        logger.warning(f"读取策略文件失败 {filename}: {e}")
                        continue
            
            # 按创建时间排序（最新的在前）
            strategies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return strategies
        
        except Exception as e:
            logger.error(f"列出策略失败: {e}")
            return []
    
    def delete_strategy(self, filename: str) -> bool:
        """
        删除策略
        
        Args:
            filename: 策略文件名
        
        Returns:
            bool: 是否删除成功
        """
        try:
            filepath = os.path.join(self.storage_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"策略已删除: {filepath}")
                return True
            else:
                logger.warning(f"策略文件不存在: {filepath}")
                return False
        
        except Exception as e:
            logger.error(f"删除策略失败: {e}")
            return False
    
    def export_strategy(self, filename: str, export_path: str) -> bool:
        """
        导出策略到指定路径
        
        Args:
            filename: 策略文件名
            export_path: 导出路径
        
        Returns:
            bool: 是否导出成功
        """
        try:
            import shutil
            
            source = os.path.join(self.storage_dir, filename)
            
            if os.path.exists(source):
                shutil.copy2(source, export_path)
                logger.info(f"策略已导出: {export_path}")
                return True
            else:
                logger.warning(f"策略文件不存在: {source}")
                return False
        
        except Exception as e:
            logger.error(f"导出策略失败: {e}")
            return False
    
    def import_strategy(self, import_path: str) -> bool:
        """
        从指定路径导入策略
        
        Args:
            import_path: 导入路径
        
        Returns:
            bool: 是否导入成功
        """
        try:
            import shutil
            
            if os.path.exists(import_path):
                filename = os.path.basename(import_path)
                destination = os.path.join(self.storage_dir, filename)
                
                shutil.copy2(import_path, destination)
                logger.info(f"策略已导入: {destination}")
                return True
            else:
                logger.warning(f"导入文件不存在: {import_path}")
                return False
        
        except Exception as e:
            logger.error(f"导入策略失败: {e}")
            return False


def main():
    """测试函数"""
    manager = StrategyManager()
    
    # 测试保存策略
    test_strategy = {
        'strategy_name': '测试策略',
        'description': '这是一个测试策略',
        'code': 'def custom_strategy(): pass',
        'explanation': '测试说明'
    }
    
    print("保存策略...")
    if manager.save_strategy(test_strategy):
        print("✓ 保存成功")
    
    # 列出所有策略
    print("\n已保存的策略:")
    strategies = manager.list_strategies()
    for s in strategies:
        print(f"  - {s['strategy_name']} ({s['filename']})")


if __name__ == "__main__":
    main()
