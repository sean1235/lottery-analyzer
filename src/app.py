"""澳洲幸运5 数据分析平台 - 精简版"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger
import os

from scraper import LotteryScraper
from utils import DatabaseManager
from custom_strategy_parser import CustomStrategyParser
from strategy_backtester import StrategyBacktester
from strategy_manager import StrategyManager

# 页面配置
st.set_page_config(
    page_title="澳洲幸运5 数据分析",
    page_icon="🎰",
    layout="wide"
)

# 标题
st.title("🎰 澳洲幸运5 数据分析平台")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 控制面板")
    
    # 1. 数据获取
    st.subheader("📥 数据获取")
    
    max_pages = st.selectbox(
        "爬取页数",
        options=[0, 5, 10, 20, 50],
        index=0,
        format_func=lambda x: "全部" if x == 0 else f"{x}页"
    )
    
    if st.button("🔄 获取数据", use_container_width=True):
        with st.spinner("正在爬取数据..."):
            try:
                scraper = LotteryScraper(headless=True, debug=False)
                count = scraper.scrape(max_pages=max_pages)
                st.success(f"✅ 成功获取 {count} 条新数据")
            except Exception as e:
                st.error(f"❌ 获取失败: {e}")
    
    st.divider()
    
    # API Key 配置
    st.subheader("🔑 API 配置")
    
    # 尝试从环境变量获取
    default_api_key = os.getenv('OPENAI_API_KEY', '')
    default_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.aabao.top/v1')
    
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=default_api_key,
        placeholder="请输入你的 API Key",
        help="支持 OpenAI 官方或兼容的第三方服务"
    )
    
    base_url = st.text_input(
        "API Base URL",
        value=default_base_url,
        placeholder="https://api.aabao.top/v1",
        help="API 服务地址。默认: https://api.aabao.top/v1"
    )
    
    if not api_key:
        st.warning("⚠️ 请输入 API Key 以使用 AI 策略生成功能")
        st.info("💡 提示：你也可以设置环境变量 OPENAI_API_KEY")

# 主内容区
# 添加刷新按钮
if st.sidebar.button("🔄 刷新数据", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

db = DatabaseManager()
df = db.get_all_data()

if df.empty:
    st.warning("⚠️ 暂无数据，请先点击【获取数据】按钮")
else:
    # 标签页
    tab1, tab2, tab3 = st.tabs(["📊 数据可视化", "🎲 策略系统", "📋 原始数据"])
    
    # ==================== 标签页1：数据可视化 ====================
    with tab1:
        st.header("📊 数据可视化分析")
        
        # 解析号码
        df['numbers_list'] = df['numbers'].apply(lambda x: [int(n) for n in x.split(',')])
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总期数", len(df))
        
        with col2:
            latest = df.iloc[0]
            st.metric("最新期号", latest['period_id'])
        
        with col3:
            latest_numbers = latest['numbers_list']
            st.metric("最新号码", ' '.join(map(str, latest_numbers)))
        
        with col4:
            latest_sum = sum(latest_numbers)
            st.metric("和值", latest_sum)
        
        st.divider()
        
        # 可视化图表
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("🔥 号码频率分布")
            
            # 统计每个号码出现的次数
            all_numbers = []
            for numbers in df['numbers_list']:
                all_numbers.extend(numbers)
            
            freq_data = pd.DataFrame({
                '号码': range(10),
                '出现次数': [all_numbers.count(i) for i in range(10)]
            })
            
            fig1 = px.bar(
                freq_data,
                x='号码',
                y='出现次数',
                title='号码频率统计',
                color='出现次数',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_b:
            st.subheader("📈 和值分布")
            
            # 计算每期的和值
            df['sum_value'] = df['numbers_list'].apply(sum)
            
            fig2 = px.histogram(
                df,
                x='sum_value',
                nbins=30,
                title='和值分布直方图',
                labels={'sum_value': '和值', 'count': '次数'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        st.divider()
        
        col_c, col_d = st.columns(2)
        
        with col_c:
            st.subheader("🎯 单双分布")
            
            # 统计单双
            df['odd_count'] = df['numbers_list'].apply(lambda x: sum(1 for n in x if n % 2 == 1))
            
            odd_dist = df['odd_count'].value_counts().sort_index()
            
            fig3 = px.pie(
                values=odd_dist.values,
                names=[f'{i}单{5-i}双' for i in odd_dist.index],
                title='单双比例分布'
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        with col_d:
            st.subheader("📊 大小分布")
            
            # 统计大小号
            df['big_count'] = df['numbers_list'].apply(lambda x: sum(1 for n in x if n >= 5))
            
            big_dist = df['big_count'].value_counts().sort_index()
            
            fig4 = px.pie(
                values=big_dist.values,
                names=[f'{i}大{5-i}小' for i in big_dist.index],
                title='大小号比例分布'
            )
            st.plotly_chart(fig4, use_container_width=True)
        
        st.divider()
        
        # 和值趋势
        st.subheader("📉 和值趋势图")
        
        # 取最近100期
        recent_df = df.head(100).iloc[::-1]  # 反转顺序，从旧到新
        
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(
            x=list(range(len(recent_df))),
            y=recent_df['sum_value'],
            mode='lines+markers',
            name='和值',
            line=dict(color='blue', width=2)
        ))
        fig5.update_layout(
            title='最近100期和值趋势',
            xaxis_title='期数',
            yaxis_title='和值',
            hovermode='x unified'
        )
        st.plotly_chart(fig5, use_container_width=True)
    
    # ==================== 标签页2：策略系统 ====================
    with tab2:
        st.header("🎲 AI 策略系统")
        
        st.info("💡 用自然语言描述你的投注策略，AI 会自动生成代码并回测")
        
        # 初始化策略管理器
        strategy_manager = StrategyManager()
        
        # 策略加载区域
        st.subheader("📂 已保存的策略")
        
        col_import, col_list = st.columns([1, 2])
        
        with col_import:
            # 导入策略
            uploaded_file = st.file_uploader(
                "导入策略文件",
                type=['json'],
                help="上传 JSON 格式的策略文件",
                key="strategy_upload"
            )
            
            # 显示示例格式
            with st.expander("📖 查看策略文件格式示例"):
                st.code('''{
  "strategy_name": "策略名称",
  "description": "策略描述",
  "code": "def custom_strategy(current_numbers, next_numbers, history, idx):\\n    return {...}",
  "explanation": "代码说明"
}''', language='json')
                st.info("💡 提示：可以先导出一个现有策略，查看完整的文件格式")
            
            if uploaded_file is not None:
                try:
                    import json
                    
                    # 读取文件内容
                    file_content = uploaded_file.read()
                    
                    # 检查文件是否为空
                    if not file_content:
                        st.error("❌ 文件为空，请选择有效的策略文件")
                    else:
                        # 解码并解析 JSON
                        try:
                            content_str = file_content.decode('utf-8')
                            strategy_data = json.loads(content_str)
                        except UnicodeDecodeError:
                            st.error("❌ 文件编码错误，请确保文件是 UTF-8 编码")
                            strategy_data = None
                        except json.JSONDecodeError as e:
                            st.error(f"❌ JSON 格式错误: {e}")
                            st.info("💡 请确保文件是有效的 JSON 格式")
                            strategy_data = None
                        
                        if strategy_data:
                            # 验证策略数据
                            required_fields = ['strategy_name', 'description', 'code', 'explanation']
                            missing_fields = [f for f in required_fields if f not in strategy_data]
                            
                            if missing_fields:
                                st.error(f"❌ 策略文件缺少必要字段: {', '.join(missing_fields)}")
                                st.info("💡 必需字段: strategy_name, description, code, explanation")
                            else:
                                # 保存导入的策略
                                if strategy_manager.save_strategy(strategy_data):
                                    st.success(f"✅ 成功导入策略: {strategy_data['strategy_name']}")
                                    st.info("💡 策略已保存，请在下拉框中选择并使用")
                                    # 不使用 st.rerun()，避免循环
                                else:
                                    st.error("❌ 保存策略失败")
                
                except Exception as e:
                    st.error(f"❌ 导入失败: {e}")
                    logger.exception("策略导入失败")
        
        with col_list:
            pass  # 占位符
        
        saved_strategies = strategy_manager.list_strategies()
        
        if saved_strategies:
            col_load1, col_load2, col_load3 = st.columns([3, 1, 1])
            
            with col_load1:
                selected_strategy = st.selectbox(
                    "选择策略",
                    options=[s['filename'] for s in saved_strategies],
                    format_func=lambda x: next(
                        (s['strategy_name'] for s in saved_strategies if s['filename'] == x),
                        x
                    )
                )
            
            with col_load2:
                st.write("")  # 占位符对齐
                st.write("")  # 占位符对齐
                if st.button("📥 加载", use_container_width=True):
                    loaded_strategy = strategy_manager.load_strategy(selected_strategy)
                    if loaded_strategy:
                        st.session_state['generated_strategy'] = loaded_strategy
                        st.success(f"✅ 已加载策略: {loaded_strategy.get('strategy_name')}")
                        st.info("💡 向下滚动查看策略代码，或使用快速回测")
                        # 不使用 st.rerun()，避免循环
                    else:
                        st.error("❌ 加载失败")
            
            with col_load3:
                st.write("")  # 占位符对齐
                st.write("")  # 占位符对齐
                
                # 导出按钮
                loaded_strategy = strategy_manager.load_strategy(selected_strategy)
                if loaded_strategy:
                    import json
                    strategy_json = json.dumps(loaded_strategy, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📤 导出",
                        data=strategy_json,
                        file_name=selected_strategy,
                        mime="application/json",
                        use_container_width=True
                    )
            
            # 第二行：快速回测和删除
            col_backtest, col_delete = st.columns(2)
            
            with col_backtest:
                # 获取数据库中的总期数
                total_data_count = len(df)
                max_backtest = max(10, total_data_count)  # 可以回测所有数据
                
                quick_backtest_periods = st.number_input(
                    "快速回测期数", 
                    min_value=10, 
                    max_value=max_backtest, 
                    value=max_backtest,  # 默认回测所有数据
                    step=10,
                    help=f"数据库共 {total_data_count} 期数据，可回测 {max_backtest} 期",
                    key="quick_backtest_periods"
                )
                
                if st.button("🚀 快速回测", use_container_width=True):
                    loaded_strategy = strategy_manager.load_strategy(selected_strategy)
                    if loaded_strategy:
                        with st.spinner("正在回测..."):
                            try:
                                backtester = StrategyBacktester()
                                results = backtester.execute_strategy(
                                    loaded_strategy.get('code', ''),
                                    periods=quick_backtest_periods
                                )
                                
                                if not results.empty:
                                    st.session_state['generated_strategy'] = loaded_strategy
                                    st.session_state['backtest_results'] = results
                                    st.session_state['backtest_summary'] = backtester.generate_summary(results)
                                    st.success("✅ 回测完成，请向下滚动查看结果")
                                    # 移除 st.rerun()，避免无限循环
                                else:
                                    st.error("❌ 回测失败")
                            except Exception as e:
                                st.error(f"❌ 回测失败: {e}")
                                logger.exception("快速回测失败")
                    else:
                        st.error("❌ 加载策略失败")
            
            with col_delete:
                st.write("")  # 占位符对齐
                st.write("")  # 占位符对齐
                st.write("")  # 占位符对齐
                if st.button("🗑️ 删除选中的策略", use_container_width=True):
                    if strategy_manager.delete_strategy(selected_strategy):
                        st.success("✅ 策略已删除")
                        st.info("💡 刷新页面以更新策略列表")
                        # 不使用 st.rerun()，避免循环
                    else:
                        st.error("❌ 删除失败")
        else:
            st.info("暂无已保存的策略")
        
        st.divider()
        
        # 策略描述输入
        st.subheader("✍️ 创建新策略")
        strategy_description = st.text_area(
            "策略描述",
            placeholder="""例如：
使用双锚定算法计算排除值。
如果前6期全部正确，且近10期正确率达到100%，最长连对大于等于6期，则判定为黄金盈利期。
在黄金盈利期，如果连对1-5期，下注1仓（300积分）；如果连对6期以上，降为0.5仓（150积分）。
如果上一期预测错误，本期强制空仓。""",
            height=200
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 生成策略代码", use_container_width=True):
                if strategy_description and api_key:
                    with st.spinner("AI 正在生成策略代码..."):
                        try:
                            parser = CustomStrategyParser(api_key=api_key, base_url=base_url if base_url else None)
                            result = parser.parse_strategy(strategy_description)
                            
                            if result.get('success'):
                                st.session_state['generated_strategy'] = result
                                st.success("✅ 策略代码生成成功")
                            else:
                                st.error(f"❌ 生成失败: {result.get('error')}")
                        except Exception as e:
                            st.error(f"❌ 生成失败: {e}")
                            logger.exception("策略生成失败")
                else:
                    st.warning("⚠️ 请输入策略描述和 API Key")
        
        with col2:
            # 获取数据库中的总期数
            total_data_count = len(df)
            max_backtest = max(10, total_data_count)  # 可以回测所有数据
            
            backtest_periods = st.number_input(
                "回测期数", 
                min_value=10, 
                max_value=max_backtest, 
                value=max_backtest,  # 默认回测所有数据
                step=10,
                help=f"数据库共 {total_data_count} 期数据，可回测 {max_backtest} 期"
            )
        
        # 显示生成的代码
        if 'generated_strategy' in st.session_state:
            strategy = st.session_state['generated_strategy']
            
            st.divider()
            st.subheader("📄 生成的策略代码")
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.write(f"**策略名称:** {strategy.get('strategy_name', 'N/A')}")
            with col_info2:
                st.write(f"**策略描述:** {strategy.get('description', 'N/A')}")
            
            st.write(f"**代码说明:** {strategy.get('explanation', 'N/A')}")
            
            # 代码显示和复制
            code_content = strategy.get('code', '')
            st.code(code_content, language='python')
            
            # 添加复制提示
            st.caption("💡 提示：点击代码框右上角的复制按钮可以正确复制代码（保留格式）")
            
            # 保存和回测按钮
            col_save, col_backtest = st.columns(2)
            
            with col_save:
                if st.button("💾 保存策略", use_container_width=True):
                    if strategy_manager.save_strategy(strategy):
                        st.success("✅ 策略已保存")
                        st.info("💡 策略已保存到列表，可以在上方加载")
                        # 不使用 st.rerun()，避免循环
                    else:
                        st.error("❌ 保存失败")
            
            with col_backtest:
                if st.button("🚀 执行回测", use_container_width=True):
                    with st.spinner("正在回测..."):
                        try:
                            backtester = StrategyBacktester()
                            results = backtester.execute_strategy(
                                strategy.get('code', ''),
                                periods=backtest_periods
                            )
                            
                            if not results.empty:
                                st.session_state['backtest_results'] = results
                                st.session_state['backtest_summary'] = backtester.generate_summary(results)
                                st.success("✅ 回测完成")
                            else:
                                st.error("❌ 回测失败")
                        except Exception as e:
                            st.error(f"❌ 回测失败: {e}")
                            logger.exception("回测失败")
        
        # 显示回测结果
        if 'backtest_results' in st.session_state and 'backtest_summary' in st.session_state:
            results = st.session_state['backtest_results']
            summary = st.session_state['backtest_summary']
            
            st.divider()
            st.subheader("📊 回测分析报告")
            
            # 添加说明
            if summary['win_rate'] == 1.0 and summary['participated'] > 0:
                st.info("""
                📌 **关于 100% 胜率的说明**
                
                这个策略采用了非常保守的参与策略，只在极其有把握的情况下才下注（参与率仅 {:.1%}）。
                
                - **胜率** = 参与并盈利的次数 / 总参与次数
                - **整体准确率** = 预测正确的次数 / 总期数（包括未参与的）
                
                100% 胜率说明策略在选择参与时机方面很谨慎，但这也意味着错过了很多潜在机会。
                实际应用时需要权衡参与率和胜率的关系。
                """.format(summary['participation_rate']))
            
            # 统计摘要
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总期数", summary['total_periods'])
            with col2:
                st.metric("参与期数", summary['participated'])
            with col3:
                st.metric("总盈亏", f"{summary['total_profit']:+.2f}",
                         delta=f"{summary['total_profit']:+.2f}",
                         delta_color="normal" if summary['total_profit'] >= 0 else "inverse")
            with col4:
                st.metric("胜率", f"{summary['win_rate']:.1%}")
                if summary['win_rate'] == 1.0 and summary['participated'] > 0:
                    st.caption("⚠️ 策略非常保守")
            
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                st.metric("参与率", f"{summary['participation_rate']:.1%}")
            with col6:
                st.metric("最大回撤", f"{summary['max_drawdown']:.2f}")
            with col7:
                st.metric("平均每注盈亏", f"{summary['avg_profit_per_bet']:+.2f}")
            with col8:
                st.metric("整体准确率", f"{summary.get('overall_accuracy', 0):.1%}",
                         help="包括未参与期数的预测准确率")
            
            st.divider()
            
            # 累计盈亏曲线
            st.subheader("📈 累计盈亏曲线")
            
            results['盈亏_数值'] = results['盈亏'].apply(lambda x: float(x) if x != '0' else 0.0)
            results['累计盈亏'] = results['盈亏_数值'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(len(results))),
                y=results['累计盈亏'],
                mode='lines+markers',
                name='累计盈亏',
                line=dict(color='green' if summary['total_profit'] >= 0 else 'red', width=2),
                fill='tozeroy'
            ))
            fig.update_layout(
                title="累计盈亏走势",
                xaxis_title="期数",
                yaxis_title="累计盈亏（积分）",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # 详细报表
            st.subheader("📋 详细回测报表")
            # 反转顺序，最新的在上面
            results_display = results.iloc[::-1].reset_index(drop=True)
            st.dataframe(results_display, use_container_width=True, height=400)
    
    # ==================== 标签页3：原始数据 ====================
    with tab3:
        st.header("📋 原始数据")
        
        st.write(f"📊 共 {len(df)} 条数据")
        
        # 搜索功能
        search_term = st.text_input("🔍 搜索期号", placeholder="输入期号进行搜索")
        
        # 准备显示数据（按时间倒序，最新在上）
        display_df = df.sort_values('draw_time', ascending=False).reset_index(drop=True)
        # 索引从1开始
        display_df.index = display_df.index + 1
        display_df = display_df[['period_id', 'draw_time', 'numbers']].copy()
        display_df.columns = ['期号', '开奖时间', '号码']
        
        # 应用搜索
        if search_term:
            display_df = display_df[display_df['期号'].str.contains(search_term, na=False)]
        
        st.write(f"显示 {len(display_df)} 条数据")
        
        # 显示数据表
        st.dataframe(display_df, use_container_width=True, height=600)

# 页脚
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
    澳洲幸运5 数据分析平台 | 数据仅供参考
</div>
""", unsafe_allow_html=True)
