import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import yaml
from datetime import datetime
import os

from scraper import LotteryScraper
from analyzer import LotteryAnalyzer
from summarizer import LotterySummarizer
from utils import setup_directories, DatabaseManager
from rule_validator import RuleValidator
from nlp_rule_parser import NLPRuleParser
from ai_rule_parser import AIRuleParser
from strategy_engine import StrategyEngine
from custom_strategy_parser import CustomStrategyParser
from strategy_backtester import StrategyBacktester

# 页面配置
st.set_page_config(
    page_title="澳洲幸运5 数据分析平台",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化目录
setup_directories()

# 加载配置
@st.cache_resource
def load_config():
    with open("config.yaml", 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()

# 自定义样式
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .hot-number {
        background-color: #FF6B6B;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        margin: 2px;
        display: inline-block;
    }
    .cold-number {
        background-color: #4ECDC4;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        margin: 2px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎰 澳洲幸运5 分析平台")
    st.divider()
    
    # 数据更新
    st.subheader("📊 数据管理")
    
    # 爬取页数设置
    max_pages_option = st.selectbox(
        "爬取页数",
        options=[0, 5, 10, 20, 50, 100],
        index=0,
        format_func=lambda x: "全部页面" if x == 0 else f"{x} 页",
        help="0 表示爬取所有可用页面，数字越大获取数据越多"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 更新数据", use_container_width=True):
            with st.spinner("正在爬取数据..."):
                try:
                    # 启用调试模式
                    scraper = LotteryScraper(headless=True, debug=True)
                    count = scraper.scrape(max_pages=max_pages_option)
                    st.success(f"✅ 成功获取 {count} 条新数据")
                    if count == 0:
                        st.warning("⚠️ 未获取到新数据，请检查日志文件 log/app.log")
                        st.info("💡 提示：页面源码已保存到 data/page_source.html，可用于调试")
                except Exception as e:
                    st.error(f"❌ 爬取失败: {e}")
                    logger.exception("爬取数据时发生错误")
    
    with col2:
        if st.button("📈 分析数据", use_container_width=True):
            with st.spinner("正在分析..."):
                try:
                    analyzer = LotteryAnalyzer()
                    patterns = analyzer.analyze(window=100)
                    analyzer.save_patterns()
                    st.success("✅ 分析完成")
                except Exception as e:
                    st.error(f"❌ 分析失败: {e}")
    
    st.divider()
    
    # 规则管理
    st.subheader("⚙️ 规则管理")
    
    rule_action = st.selectbox(
        "选择操作",
        ["查看规则有效度", "添加新规则", "编辑规则", "删除规则"],
        key="rule_action"
    )
    
    if rule_action == "查看规则有效度":
        if st.button("🔍 验证所有规则", use_container_width=True):
            with st.spinner("正在验证规则..."):
                try:
                    validator = RuleValidator()
                    st.session_state['rule_validation'] = validator.validate_all_rules(window=100)
                    st.success("✅ 验证完成")
                except Exception as e:
                    st.error(f"❌ 验证失败: {e}")
    
    elif rule_action == "添加新规则":
        st.write("### 📝 添加新规则")
        
        # 选择输入方式
        input_method = st.radio(
            "选择输入方式",
            ["🗣️ 自然语言描述", "💻 直接输入条件表达式"],
            horizontal=True
        )
        
        if input_method == "🗣️ 自然语言描述":
            # 自然语言输入
            st.info("💡 用中文描述你的规则，系统会自动转换为条件表达式")
            
            # AI 解析选项
            use_ai = st.checkbox(
                "🤖 使用 AI 智能解析（更强大，支持复杂描述）",
                value=False,
                help="需要配置 OpenAI API Key"
            )
            
            # API Key 配置
            api_key = None
            if use_ai:
                api_key_input = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    value="sk-DGSBXqgsXGVeyoU5LQyth3eQcEQFxFSRBgfaboOtVfd1gBTE",
                    help="输入你的 OpenAI API Key"
                )
                if api_key_input:
                    api_key = api_key_input
            
            # 显示示例
            with st.expander("📖 查看示例"):
                parser = AIRuleParser()
                st.markdown(parser.get_prompt_for_user())
            
            natural_input = st.text_area(
                "规则描述",
                placeholder="例如：和值大于25并且单数至少3个",
                height=100,
                key="natural_rule_input"
            )
            
            # 实时解析预览
            if natural_input:
                with st.spinner("正在解析..."):
                    parser = AIRuleParser(api_key=api_key)
                    parse_result = parser.parse(natural_input, use_ai=use_ai)
                    
                    if parse_result.get('condition'):
                        st.success("✅ 解析成功")
                        st.code(parse_result['condition'], language="python")
                        
                        # 显示详细信息
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"置信度: {parse_result.get('confidence', 0):.0%}")
                        with col2:
                            method = "AI 解析" if parse_result.get('method') == 'ai_raw' or use_ai else "模式匹配"
                            st.caption(f"方法: {method}")
                        
                        if parse_result.get('explanation'):
                            st.info(f"💡 {parse_result['explanation']}")
                        
                        # 保存解析结果到 session state
                        st.session_state['parsed_condition'] = parse_result['condition']
                        st.session_state['parsed_explanation'] = parse_result.get('explanation', '')
                    else:
                        st.error("❌ 无法解析")
                        if 'error' in parse_result:
                            st.warning(parse_result['error'])
                        if 'suggestions' in parse_result:
                            st.info("💡 试试这些示例：")
                            for example in parse_result['suggestions'][:3]:
                                st.text(f"  • {example}")
            
            # 规则详情
            with st.form("add_natural_rule_form"):
                new_rule_name = st.text_input("规则名称", placeholder="例如：高和值追单")
                new_rule_alert = st.text_input("触发提示", placeholder="规则命中时的提示信息")
                new_rule_enabled = st.checkbox("启用规则", value=True)
                
                submitted = st.form_submit_button("添加规则", use_container_width=True)
                if submitted:
                    if new_rule_name and 'parsed_condition' in st.session_state:
                        new_rule = {
                            'name': new_rule_name,
                            'description': natural_input,
                            'condition': st.session_state['parsed_condition'],
                            'alert': new_rule_alert,
                            'enabled': new_rule_enabled
                        }
                        validator = RuleValidator()
                        if validator.add_rule(new_rule):
                            st.success(f"✅ 规则 '{new_rule_name}' 已添加")
                            # 清除 session state
                            if 'parsed_condition' in st.session_state:
                                del st.session_state['parsed_condition']
                            if 'parsed_explanation' in st.session_state:
                                del st.session_state['parsed_explanation']
                            st.rerun()
                        else:
                            st.error("❌ 添加失败")
                    else:
                        st.warning("⚠️ 请填写规则名称并输入有效的规则描述")
        
        else:
            # 直接输入条件表达式
            with st.form("add_rule_form"):
                st.write("直接输入条件表达式")
                new_rule_name = st.text_input("规则名称", placeholder="例如：高和值追单")
                new_rule_desc = st.text_input("规则描述", placeholder="简短描述规则的含义")
                new_rule_condition = st.text_input(
                    "规则条件", 
                    placeholder="例如：sum > 22 AND odd_count >= 3",
                    help="可用变量：sum, odd_count, even_count, big_count, small_count, has_duplicate, has_sequence"
                )
                new_rule_alert = st.text_input("触发提示", placeholder="规则命中时的提示信息")
                new_rule_enabled = st.checkbox("启用规则", value=True)
                
                submitted = st.form_submit_button("添加规则")
                if submitted:
                    if new_rule_name and new_rule_condition:
                        new_rule = {
                            'name': new_rule_name,
                            'description': new_rule_desc,
                            'condition': new_rule_condition,
                            'alert': new_rule_alert,
                            'enabled': new_rule_enabled
                        }
                        validator = RuleValidator()
                        if validator.add_rule(new_rule):
                            st.success(f"✅ 规则 '{new_rule_name}' 已添加")
                            st.rerun()
                        else:
                            st.error("❌ 添加失败")
                    else:
                        st.warning("⚠️ 请填写规则名称和条件")
                    st.warning("⚠️ 请填写规则名称和条件")
    
    st.divider()
    
    # 用户提示词查询
    st.subheader("🔍 快速查询")
    query = st.text_input("输入提示词（如：热号、冷号、长龙）", placeholder="例如：最近热号连开情况")
    
    st.divider()
    
    # 导出功能
    st.subheader("📥 导出报告")
    if st.button("导出 Excel", use_container_width=True):
        st.info("导出功能开发中...")
    
    if st.button("导出 PDF", use_container_width=True):
        st.info("导出功能开发中...")

# ==================== 主内容区 ====================

# 加载数据
db = DatabaseManager()
df = db.get_all_data()

if df.empty:
    st.warning("⚠️ 暂无数据，请先点击侧边栏的【更新数据】按钮")
else:
    # 加载分析结果
    try:
        with open("data/summary.json", 'r', encoding='utf-8') as f:
            patterns = json.load(f)
    except:
        patterns = {}
    
    # 标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 实时数据", 
        "📈 规律分析", 
        "🎯 规则匹配", 
        "📋 详细报告", 
        "✅ 规则验证",
        "🎲 投注策略"
    ])
    
    # 显示数据统计信息
    st.info(f"💾 数据库共有 {len(df)} 条开奖记录")
    
    # ==================== 标签页1：实时数据 ====================
    with tab1:
        st.subheader("最新开奖结果")
        
        if not df.empty:
            latest = df.iloc[0]
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("最新期号", latest['period_id'])
            with col2:
                st.metric("开奖时间", latest['draw_time'][:10])
            with col3:
                numbers = [int(x) for x in latest['numbers'].split(',')]
                st.metric("开奖号码", " ".join(map(str, numbers)))
            
            st.divider()
            
            # 历史开奖数据表 - 默认显示全部数据
            st.subheader("历史开奖记录")
            
            st.write(f"📊 共 {len(df)} 条数据")
            
            # 准备显示数据 - 显示全部
            display_df = df[['period_id', 'draw_time', 'numbers']].copy()
            display_df.columns = ['期号', '开奖时间', '号码']
            
            # 使用可滚动的数据表，显示全部数据
            st.dataframe(display_df, use_container_width=True, height=600)
    
    # ==================== 标签页2：规律分析 ====================
    with tab2:
        if patterns:
            std_patterns = patterns.get('standard_patterns', {})
            
            # 频率分析
            st.subheader("🔥 频率分析")
            freq = std_patterns.get('frequency', {})
            
            col1, col2, col3 = st.columns(3)
            with col1:
                hot = freq.get('hot_numbers', [])
                st.markdown(f"**热号:** {' '.join(map(str, hot))}", unsafe_allow_html=True)
            with col2:
                cold = freq.get('cold_numbers', [])
                st.markdown(f"**冷号:** {' '.join(map(str, cold))}", unsafe_allow_html=True)
            with col3:
                st.markdown(f"**数据周期:** {patterns.get('total_periods', 0)} 期")
            
            # 频率柱状图
            freq_dict = freq.get('frequency_dict', {})
            if freq_dict:
                freq_data = {
                    'number': list(freq_dict.keys()),
                    'frequency': [freq_dict[k]['frequency'] for k in freq_dict.keys()]
                }
                fig = px.bar(freq_data, x='number', y='frequency', 
                           title="号码频率分布", labels={'frequency': '频率', 'number': '号码'})
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # 分布分析
            st.subheader("📊 分布分析")
            dist = std_patterns.get('distribution', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                odd_even = dist.get('odd_even_ratio', {})
                if odd_even:
                    fig = px.pie(
                        values=list(odd_even.values()),
                        names=list(odd_even.keys()),
                        title="单双比例分布"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                sum_range = dist.get('sum_range', {})
                if sum_range:
                    fig = px.pie(
                        values=list(sum_range.values()),
                        names=list(sum_range.keys()),
                        title="和值区间分布"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # 长龙分析
            st.subheader("🐉 长龙分析")
            dragon = std_patterns.get('long_dragon', {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("最长单数连开", f"{dragon.get('max_odd_streak', 0)} 期")
            with col2:
                st.metric("最长双数连开", f"{dragon.get('max_even_streak', 0)} 期")
            
            st.divider()
            
            # 统计检验
            st.subheader("🔬 统计检验")
            test = std_patterns.get('statistical_test', {})
            
            col1, col2, col3 = st.columns(3)
            with col1:
                p_value = test.get('p_value', 0)
                st.metric("卡方检验 p值", f"{p_value:.4f}")
            with col2:
                is_random = test.get('is_random', True)
                status = "✅ 随机" if is_random else "⚠️ 可能存在规律"
                st.markdown(f"**随机性:** {status}")
            with col3:
                sig = test.get('significance', '')
                st.markdown(f"**显著性:** {sig if sig else '无'}")
        else:
            st.info("📊 请先点击【分析数据】按钮生成分析结果")
    
    # ==================== 标签页3：规则匹配 ====================
    with tab3:
        st.subheader("🎯 用户规则匹配")
        
        summarizer = LotterySummarizer()
        
        if not df.empty:
            latest_numbers = [int(x) for x in df.iloc[0]['numbers'].split(',')]
            latest_period = df.iloc[0]['period_id']
            
            matched_rules = summarizer.matcher.match_rules(latest_period, latest_numbers)
            
            if matched_rules:
                st.success(f"✅ 本期命中 {len(matched_rules)} 条规则")
                for rule in matched_rules:
                    with st.container():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.markdown(f"**{rule['rule_name']}**")
                        with col2:
                            st.markdown(f"*{rule['alert']}*")
            else:
                st.info("ℹ️ 本期未命中任何规则")
            
            st.divider()
            
            # 规则列表
            st.subheader("已启用的规则")
            rules = summarizer.matcher.rules
            
            for rule in rules:
                if rule.get('enabled', True):
                    with st.expander(f"📌 {rule['name']}"):
                        st.write(f"**描述:** {rule.get('description', 'N/A')}")
                        st.write(f"**条件:** `{rule['condition']}`")
                        st.write(f"**提示:** {rule['alert']}")
        else:
            st.warning("⚠️ 暂无数据")
    
    # ==================== 标签页4：详细报告 ====================
    with tab4:
        st.subheader("📋 完整分析报告")
        
        if patterns:
            summarizer = LotterySummarizer()
            report = summarizer.generate_report(patterns)
            
            st.markdown(f"**更新时间:** {report['timestamp']}")
            st.markdown(f"**数据范围:** {report['period_range']}")
            
            st.divider()
            
            st.markdown("### 规律总结")
            st.info(report['natural_summary'])
            
            st.divider()
            
            st.markdown("### 完整数据表")
            
            # 添加数据筛选和搜索功能
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("🔍 搜索期号", placeholder="输入期号进行搜索")
            with col2:
                date_filter = st.date_input("📅 筛选日期", value=None)
            
            # 准备完整数据
            full_df = df[['period_id', 'draw_time', 'numbers']].copy()
            full_df.columns = ['期号', '开奖时间', '号码']
            
            # 应用搜索过滤
            if search_term:
                full_df = full_df[full_df['期号'].str.contains(search_term, na=False)]
            
            # 应用日期过滤
            if date_filter:
                full_df['日期'] = pd.to_datetime(full_df['开奖时间']).dt.date
                full_df = full_df[full_df['日期'] == date_filter]
                full_df = full_df.drop('日期', axis=1)
            
            st.write(f"📊 显示 {len(full_df)} 条数据（总共 {len(df)} 条）")
            
            # 显示完整数据表，带滚动条，显示全部数据
            st.dataframe(full_df, use_container_width=True, height=600)
            
            st.divider()
            
            st.markdown("### 原始分析数据")
            with st.expander("查看 JSON 格式"):
                st.json(patterns)
        else:
            st.info("📊 请先点击【分析数据】按钮生成分析结果")
    
    # ==================== 标签页5：规则验证 ====================
    with tab5:
        st.subheader("✅ 规则有效性验证")
        
        if 'rule_validation' in st.session_state and st.session_state['rule_validation']:
            results = st.session_state['rule_validation']
            
            st.info(f"📊 共验证 {len(results)} 条规则（基于最近 100 期数据）")
            
            # 显示规则验证结果
            for idx, result in enumerate(results):
                with st.expander(f"🔍 {result['rule_name']} - 有效性: {result['effectiveness']}", expanded=(idx==0)):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("命中率", f"{result['hit_rate']}%")
                    with col2:
                        st.metric("命中次数", f"{result['hit_count']}/{result['total_periods']}")
                    with col3:
                        st.metric("最长连续命中", f"{result['max_streak']} 期")
                    with col4:
                        st.metric("最长未命中间隔", f"{result['max_gap']} 期")
                    
                    st.divider()
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**规则描述**")
                        st.write(result['description'] if result['description'] else "无描述")
                    with col_b:
                        st.markdown("**规则条件**")
                        st.code(result['condition'], language="python")
                    
                    st.divider()
                    
                    st.markdown("**最近命中记录（最多显示10条）**")
                    if result['matched_periods']:
                        matched_df = pd.DataFrame(result['matched_periods'])
                        matched_df.columns = ['期号', '号码', '开奖时间']
                        matched_df['号码'] = matched_df['号码'].apply(lambda x: ' '.join(map(str, x)))
                        st.dataframe(matched_df, use_container_width=True)
                    else:
                        st.warning("该规则在验证期间内未命中")
                    
                    st.divider()
                    
                    # 有效性评估说明
                    st.markdown("**有效性评估说明**")
                    st.write("""
                    - ⭐⭐⭐⭐⭐ 极高：命中率高、连续性好、稳定性强
                    - ⭐⭐⭐⭐ 高：命中率较高、有一定连续性
                    - ⭐⭐⭐ 中等：命中率中等、偶尔连续命中
                    - ⭐⭐ 较低：命中率较低、连续性差
                    - ⭐ 低：命中率很低、几乎不连续
                    """)
            
            st.divider()
            
            # 规则对比图表
            st.subheader("📊 规则对比分析")
            
            chart_data = pd.DataFrame({
                '规则名称': [r['rule_name'] for r in results],
                '命中率(%)': [r['hit_rate'] for r in results],
                '命中次数': [r['hit_count'] for r in results]
            })
            
            fig = px.bar(chart_data, x='规则名称', y='命中率(%)', 
                        title="规则命中率对比",
                        labels={'命中率(%)': '命中率 (%)', '规则名称': '规则'},
                        text='命中率(%)')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("💡 请在侧边栏选择【查看规则有效度】并点击【验证所有规则】按钮")
            
            st.markdown("### 📖 使用说明")
            st.write("""
            1. 在侧边栏的【规则管理】中选择【查看规则有效度】
            2. 点击【🔍 验证所有规则】按钮
            3. 系统会分析每个规则在历史数据中的表现
            4. 查看命中率、连续性、稳定性等指标
            5. 根据有效性评级调整或优化规则
            """)
            
            st.markdown("### 📝 可用条件变量")
            st.code("""
sum          - 5个号码的总和 (0-45)
odd_count    - 单数个数 (0-5)
even_count   - 双数个数 (0-5)
big_count    - 大号(5-9)个数 (0-5)
small_count  - 小号(0-4)个数 (0-5)
has_duplicate - 是否有重复号码 (True/False)
has_sequence  - 最长连续号码长度 (1-5)
            """, language="python")
    
    # ==================== 标签页6：投注策略 ====================
    with tab6:
        st.subheader("🎲 投注策略分析")
        
        # 选择策略类型
        strategy_type = st.radio(
            "选择策略类型",
            ["📝 自定义策略（AI生成）", "🔧 预设策略"],
            horizontal=True
        )
        
        if strategy_type == "📝 自定义策略（AI生成）":
            st.info("💡 用自然语言描述你的投注策略，AI 会自动生成代码并回测")
            
            # API Key 配置
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                value="sk-DGSBXqgsXGVeyoU5LQyth3eQcEQFxFSRBgfaboOtVfd1gBTE",
                help="输入你的 OpenAI API Key"
            )
            
            # 策略描述输入
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
                                parser = CustomStrategyParser(api_key=api_key)
                                result = parser.parse_strategy(strategy_description)
                                
                                if result.get('success'):
                                    st.session_state['generated_strategy'] = result
                                    st.success("✅ 策略代码生成成功")
                                else:
                                    st.error(f"❌ 生成失败: {result.get('error')}")
                            except Exception as e:
                                st.error(f"❌ 生成失败: {e}")
                    else:
                        st.warning("⚠️ 请输入策略描述和 API Key")
            
            with col2:
                backtest_periods = st.number_input("回测期数", min_value=10, max_value=100, value=20, step=10)
            
            # 显示生成的代码
            if 'generated_strategy' in st.session_state:
                strategy = st.session_state['generated_strategy']
                
                st.divider()
                st.markdown("### 📄 生成的策略代码")
                
                with st.expander("查看策略说明", expanded=True):
                    st.write(f"**策略名称:** {strategy.get('strategy_name', 'N/A')}")
                    st.write(f"**策略描述:** {strategy.get('description', 'N/A')}")
                    st.write(f"**代码说明:** {strategy.get('explanation', 'N/A')}")
                
                st.code(strategy.get('code', ''), language='python')
                
                # 回测按钮
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
                                st.error("❌ 回测失败，未生成结果")
                        except Exception as e:
                            st.error(f"❌ 回测失败: {e}")
                            logger.exception("回测失败")
            
            # 显示回测结果
            if 'backtest_results' in st.session_state and 'backtest_summary' in st.session_state:
                results = st.session_state['backtest_results']
                summary = st.session_state['backtest_summary']
                
                st.divider()
                st.markdown("### 📊 回测结果")
                
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
                
                col5, col6, col7, col8 = st.columns(4)
                
                with col5:
                    st.metric("参与率", f"{summary['participation_rate']:.1%}")
                with col6:
                    st.metric("最大回撤", f"{summary['max_drawdown']:.2f}")
                with col7:
                    st.metric("平均每注盈亏", f"{summary['avg_profit_per_bet']:+.2f}")
                with col8:
                    win_count = summary['win_count']
                    loss_count = summary['participated'] - win_count
                    st.metric("胜/负", f"{win_count}/{loss_count}")
                
                st.divider()
                
                # 详细报表
                st.markdown("### 📋 详细回测报表")
                st.dataframe(results, use_container_width=True, height=400)
                
                st.divider()
                
                # 累计盈亏曲线
                st.markdown("### 📈 累计盈亏曲线")
                
                results['盈亏_数值'] = results['盈亏'].apply(lambda x: float(x) if x != '0' else 0.0)
                results['累计盈亏'] = results['盈亏_数值'].cumsum()
                
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(results))),
                    y=results['累计盈亏'],
                    mode='lines+markers',
                    name='累计盈亏',
                    line=dict(color='blue', width=2),
                    fill='tozeroy'
                ))
                fig.update_layout(
                    title="累计盈亏走势",
                    xaxis_title="期数",
                    yaxis_title="累计盈亏（积分）",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            # 预设策略（原有的固定策略）
            st.info("""
            📖 策略说明：
            - 基于双锚定算法的多期数据分析
            - 自动判定盘面等级（黄金盈利期、稳定盈利期、观察期、混乱期）
            - 智能风控和仓位管理
            - 实时盈亏核算
            """)
            
            # 分析周期选择
            col1, col2 = st.columns(2)
            with col1:
                analysis_periods = st.slider("分析期数", min_value=10, max_value=100, value=20, step=10)
            with col2:
                if st.button("🔍 生成策略分析", use_container_width=True):
                    with st.spinner("正在分析..."):
                        try:
                            engine = StrategyEngine()
                            st.session_state['strategy_report'] = engine.generate_strategy_report(periods=analysis_periods)
                            st.success("✅ 分析完成")
                        except Exception as e:
                            st.error(f"❌ 分析失败: {e}")
                            logger.exception("策略分析失败")
            
            if 'strategy_report' in st.session_state and not st.session_state['strategy_report'].empty:
                report = st.session_state['strategy_report']
                
                # 统计摘要
                st.divider()
                st.markdown("### 📊 策略统计摘要")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_periods = len(report)
                    st.metric("分析期数", total_periods)
                
                with col2:
                    participated = len(report[report['下注金额'] != '0'])
                    st.metric("参与期数", participated)
                
                with col3:
                    total_profit = report['盈亏'].apply(lambda x: float(x) if x != '0' else 0.0).sum()
                    st.metric("总盈亏", f"{total_profit:+.2f}", 
                             delta=f"{total_profit:+.2f}",
                             delta_color="normal" if total_profit >= 0 else "inverse")
                
                with col4:
                    win_rate = len(report[report['盈亏'].str.contains(r'^\+', regex=True)]) / participated if participated > 0 else 0
                    st.metric("胜率", f"{win_rate:.1%}")
                
                st.divider()
                
                # 详细报表
                st.markdown("### 📋 详细策略报表")
                
                # 添加筛选
                filter_col1, filter_col2 = st.columns(2)
                with filter_col1:
                    level_filter = st.multiselect(
                        "筛选盘面等级",
                        options=report['盘面等级'].unique().tolist(),
                        default=report['盘面等级'].unique().tolist()
                    )
                with filter_col2:
                    result_filter = st.multiselect(
                        "筛选双锚定结果",
                        options=['✓', '✗'],
                        default=['✓', '✗']
                    )
                
                # 应用筛选
                filtered_report = report[
                    (report['盘面等级'].isin(level_filter)) &
                    (report['双锚定结果'].isin(result_filter))
                ]
                
                # 显示报表
                st.dataframe(
                    filtered_report,
                    use_container_width=True,
                    height=500,
                    column_config={
                        "盈亏": st.column_config.NumberColumn(
                            "盈亏",
                            format="%.2f",
                        )
                    }
                )
                
                st.divider()
                
                # 盈亏曲线
                st.markdown("### 📈 累计盈亏曲线")
                
                # 计算累计盈亏
                report['累计盈亏'] = report['盈亏'].apply(lambda x: float(x) if x != '0' else 0.0).cumsum()
                
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(report))),
                    y=report['累计盈亏'],
                    mode='lines+markers',
                    name='累计盈亏',
                    line=dict(color='blue', width=2),
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
                
                # 盘面等级分布
                st.markdown("### 📊 盘面等级分布")
                
                level_counts = report['盘面等级'].value_counts()
                fig2 = px.pie(
                    values=level_counts.values,
                    names=level_counts.index,
                    title="盘面等级分布"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            else:
                st.info("💡 点击【生成策略分析】按钮开始分析")
            
            st.markdown("### 📖 策略规则说明")
            
            with st.expander("🎯 排除值计算方法"):
                st.markdown("""
                **原核心算法：**
                - N期开奖号和值 ÷ 4 取余数 = N+1期当期排除值
                
                **双锚定算法：**
                - S = (d1+d5) + (d2+d4)
                - D = |d5-d4|
                - (S+D) ÷ 4 取余数 = N+1期当期排除值
                
                **判定标准：**
                - N+1期开奖号后两位 ÷ 4 取余数 ≠ 当期排除值 → 正确
                - N+1期开奖号后两位 ÷ 4 取余数 = 当期排除值 → 错误
                """)
            
            with st.expander("📊 盘面等级判定"):
                st.markdown("""
                **黄金盈利期：**
                - 前6期全部正确，无对错交替
                - 近10期正确率100%，最长连对≥6期
                
                **稳定盈利期：**
                - 前6期全部正确，无对错交替
                - 近10期正确率≥90%，最长连对≥3期
                
                **观察期：**
                - 前6期无连续错误≥2期
                - 近10期正确率≥40%
                
                **混乱期：**
                - 前6期出现对错交替
                - 或前6期出现连续错误≥2期
                """)
            
            with st.expander("💰 仓位管理策略"):
                st.markdown("""
                **黄金盈利期：**
                - 连对1-5期：1仓（300积分）
                - 连对≥6期：0.5仓（150积分，后期降仓）
                
                **稳定盈利期：**
                - 连对1-3期：0.5仓（150积分）
                - 连对≥4期：0.3仓（90积分，后期降仓）
                
                **观察期/混乱期：**
                - 0仓（空仓）
                """)
            
            with st.expander("🚫 参与规则优先级"):
                st.markdown("""
                **优先级1（最高）：** 混乱期强制禁止
                
                **优先级2：** 上期错误单独空仓
                
                **优先级3：** Y原≠Y双 且处于盈利期 → 可参与
                
                **优先级4：** 连续2期Y原=Y双 且双锚定连续正确 → 可参与
                
                **优先级5（最低）：** 其他情况强制空仓
                """)

# 页脚
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
    澳洲幸运5 数据分析平台 v1.0 | 数据仅供参考 | 理性投资
</div>
""", unsafe_allow_html=True)
