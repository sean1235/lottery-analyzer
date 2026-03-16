import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from loguru import logger
import pandas as pd
from utils import DataValidator, DatabaseManager


class LotteryScraper:
    """澳洲幸运5 数据爬虫"""
    
    def __init__(self, headless: bool = True, debug: bool = False):
        self.url = "https://77180d.com/view/aozxy5/ssc_kjhistory.html"
        self.headless = headless
        self.debug = debug
        self.driver = None
        self.db = DatabaseManager()
        self.validator = DataValidator()
    
    def _init_driver(self):
        """初始化浏览器驱动"""
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("浏览器驱动初始化成功")
        except Exception as e:
            logger.error(f"浏览器驱动初始化失败: {e}")
            raise
    
    def _parse_table_row(self, row) -> dict:
        """解析表格行"""
        try:
            # 先获取所有文本，避免 stale element 问题
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:
                return None
            
            # 立即提取文本内容
            period_id = cells[0].text.strip()
            draw_time = cells[1].text.strip()
            numbers_text = cells[2].text.strip()
            
            # 跳过空行或标题行
            if not period_id or not numbers_text:
                return None
            
            # 解析号码
            try:
                numbers = [int(x) for x in numbers_text.split()]
            except ValueError:
                logger.warning(f"号码解析失败: {numbers_text}")
                return None
            
            # 校验数据
            if not self.validator.validate_period(period_id):
                logger.warning(f"期号格式错误: {period_id}")
                return None
            
            if not self.validator.validate_numbers(numbers):
                logger.warning(f"号码格式错误: {numbers}")
                return None
            
            if not self.validator.validate_timestamp(draw_time):
                logger.warning(f"时间戳格式错误: {draw_time}")
                return None
            
            return {
                "period_id": period_id,
                "draw_time": draw_time,
                "numbers": numbers
            }
        except Exception as e:
            logger.debug(f"解析表格行失败: {e}")
            return None
    
    def scrape(self, max_pages: int = 0, retry_times: int = 3) -> int:
        """爬取数据"""
        self._init_driver()
        scraped_count = 0
        page = 1
        
        try:
            logger.info(f"开始访问: {self.url}")
            self.driver.get(self.url)
            time.sleep(3)  # 增加等待时间
            
            # 打印页面标题确认加载成功
            logger.info(f"页面标题: {self.driver.title}")
            
            # 调试模式：保存页面源码
            if self.debug:
                with open("data/page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info("页面源码已保存到 data/page_source.html")
            
            while True:
                if max_pages > 0 and page > max_pages:
                    break
                
                logger.info(f"正在爬取第 {page} 页...")
                
                try:
                    # 等待表格加载
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                    )
                    
                    # 尝试多种选择器查找表格
                    rows = []
                    try:
                        rows = self.driver.find_elements(By.XPATH, "//table//tr")
                        logger.info(f"找到 {len(rows)} 行数据")
                    except:
                        rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
                        logger.info(f"使用 CSS 选择器找到 {len(rows)} 行数据")
                    
                    if len(rows) == 0:
                        logger.warning("未找到任何表格行")
                        break
                    
                    # 跳过表头
                    data_rows = rows[1:] if len(rows) > 1 else rows
                    
                    parsed_count = 0
                    for idx, row in enumerate(data_rows):
                        try:
                            data = self._parse_table_row(row)
                            if data:
                                parsed_count += 1
                                logger.debug(f"解析成功: {data}")
                                if self.db.insert_raw_data(data["period_id"], data["draw_time"], data["numbers"]):
                                    scraped_count += 1
                                    if scraped_count % 10 == 0:
                                        logger.info(f"已获取 {scraped_count} 条新数据")
                        except Exception as e:
                            logger.debug(f"处理第 {idx} 行时出错: {e}")
                            continue
                    
                    logger.info(f"本页解析成功 {parsed_count} 行，新增 {scraped_count} 条数据")
                    
                    # 尝试点击下一页
                    try:
                        next_btn = self.driver.find_element(By.XPATH, "//a[contains(text(), '下一页') or contains(@class, 'next')]")
                        if "disabled" in next_btn.get_attribute("class") or not next_btn.is_enabled():
                            logger.info("已到达最后一页")
                            break
                        next_btn.click()
                        time.sleep(2)
                        page += 1
                    except:
                        logger.info("未找到下一页按钮，爬取完成")
                        break
                
                except Exception as e:
                    logger.error(f"第 {page} 页爬取失败: {e}")
                    if retry_times > 0:
                        retry_times -= 1
                        logger.info(f"重试中... (剩余 {retry_times} 次)")
                        time.sleep(2)
                        continue
                    else:
                        break
            
            logger.info(f"爬取完成，共获取 {scraped_count} 条新数据")
            return scraped_count
        
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """主函数"""
    scraper = LotteryScraper(headless=True)
    scraper.scrape(max_pages=10)


if __name__ == "__main__":
    main()
