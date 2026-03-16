import os
import sqlite3
import pandas as pd
from datetime import datetime
from loguru import logger

log_dir = "log"
os.makedirs(log_dir, exist_ok=True)
logger.add(f"{log_dir}/app.log", rotation="500 MB", retention=5)


class DataValidator:
    @staticmethod
    def validate_period(period_id: str) -> bool:
        return bool(period_id and period_id.strip() and any(c.isdigit() for c in period_id))
    
    @staticmethod
    def validate_numbers(numbers: list) -> bool:
        if len(numbers) != 5:
            return False
        for num in numbers:
            if not (0 <= num <= 9):
                return False
        return True
    
    @staticmethod
    def validate_timestamp(timestamp: str) -> bool:
        return bool(timestamp and timestamp.strip())


class DatabaseManager:
    def __init__(self, db_path: str = "data/patterns.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id TEXT UNIQUE NOT NULL,
                draw_time TEXT NOT NULL,
                numbers TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id TEXT UNIQUE NOT NULL,
                sum_value INTEGER,
                odd_count INTEGER,
                even_count INTEGER,
                big_count INTEGER,
                small_count INTEGER,
                has_duplicate BOOLEAN,
                has_sequence BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value TEXT,
                period_range TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def insert_raw_data(self, period_id: str, draw_time: str, numbers: list) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            numbers_str = ",".join(map(str, numbers))
            cursor.execute("""
                INSERT OR IGNORE INTO raw_data (period_id, draw_time, numbers)
                VALUES (?, ?, ?)
            """, (period_id, draw_time, numbers_str))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"插入数据失败: {e}")
            return False
    
    def get_all_data(self) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM raw_data ORDER BY draw_time ASC", conn)
            conn.close()
            
            if not df.empty and len(df) > 1:
                if df.iloc[0]['draw_time'] > df.iloc[-1]['draw_time']:
                    logger.warning("⚠️ 数据顺序异常，正在修复...")
                    df = df.sort_values('draw_time', ascending=True).reset_index(drop=True)
            
            return df
        except Exception as e:
            logger.error(f"读取数据失败: {e}")
            return pd.DataFrame()
    
    def get_latest_period(self) -> str:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT period_id FROM raw_data ORDER BY draw_time DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"获取最新期号失败: {e}")
            return None


def setup_directories():
    dirs = ["data", "log"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
    logger.info("目录结构已准备")
