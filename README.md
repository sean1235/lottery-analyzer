# 澳洲幸运5 数据分析平台

## 在线访问

部署到 Streamlit Cloud 后，任何人都可以通过网址直接使用！

### 快速部署步骤：
1. 访问 [Streamlit Cloud](https://share.streamlit.io)
2. 用 GitHub 账号登录
3. 选择这个仓库进行部署
4. Main file path 设置为：`src/app.py`
5. 点击 Deploy

几分钟后，你会得到一个公开网址，分享给任何人都可以直接打开使用！

## 项目简介

一个「一键全自动」的澳洲幸运5数据分析平台，实现：
- 🔄 自动数据采集
- 📊 智能规律分析  
- 📈 交互式可视化
- 🎯 自定义规则匹配
- 🎲 AI策略生成与回测

## 主要功能

### 1. 数据采集
- 自动爬取历史开奖数据
- 增量更新，避免重复
- 失败自动重试

### 2. 规律分析
- 频率分析（热号、冷号）
- 分布分析（单双比例、和值区间）
- 长龙分析（连续单数/双数）
- 统计检验（卡方检验）

### 3. 规则系统
- 支持自然语言描述规则
- AI 自动转换为条件表达式
- 规则有效性验证
- 历史命中率分析

### 4. 投注策略
- AI 自然语言生成策略代码
- 策略回测功能
- 盈亏分析和可视化
- 风险控制建议

## 技术栈

- **前端**: Streamlit
- **数据处理**: Pandas, NumPy
- **可视化**: Plotly
- **爬虫**: Selenium
- **数据库**: SQLite
- **AI**: OpenAI API

## 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/sean1235/lottery-analyzer.git
cd lottery-analyzer

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行应用
streamlit run src/app.py
```

浏览器会自动打开 http://localhost:8501

## 云端部署

### 方案一：Streamlit Cloud（推荐，免费）

1. Fork 这个仓库到你的 GitHub 账号
2. 访问 https://share.streamlit.io
3. 用 GitHub 登录
4. 点击 "New app"
5. 选择你 fork 的仓库
6. Main file path: `src/app.py`
7. 点击 "Deploy"

等待几分钟，你会得到一个公开网址！

### 方案二：Railway

1. 访问 https://railway.app
2. 用 GitHub 登录
3. 点击 "New Project" > "Deploy from GitHub repo"
4. 选择这个仓库
5. Railway 会自动检测并部署

### 方案三：Render

1. 访问 https://render.com
2. 用 GitHub 登录
3. 点击 "New" > "Web Service"
4. 连接这个仓库
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0`

## 项目结构

```
.
├── README.md                 # 项目说明
├── requirements.txt          # Python依赖
├── packages.txt              # 系统依赖（Streamlit Cloud）
├── config.yaml               # 用户配置
├── .streamlit/
│   └── config.toml          # Streamlit配置
├── src/                      # 源代码
│   ├── app.py               # 主应用
│   ├── scraper.py           # 数据爬虫
│   ├── analyzer.py          # 数据分析
│   ├── summarizer.py        # 总结生成
│   ├── utils.py             # 工具函数
│   ├── rule_validator.py    # 规则验证
│   ├── strategy_engine.py   # 策略引擎
│   └── strategy_manager.py  # 策略管理
├── data/                     # 数据存储（自动创建）
└── log/                      # 日志文件（自动创建）
```

## 常见问题

**Q: 部署后数据会丢失吗？**  
A: Streamlit Cloud 免费版会在重启时清空数据。如需持久化，可以连接云数据库（如 Supabase）。

**Q: 可以自定义规则吗？**  
A: 可以！在界面左侧的「规则管理」中添加自定义规则，支持自然语言描述。

**Q: 支持哪些分析功能？**  
A: 频率分析、分布分析、长龙分析、统计检验、规则匹配、策略回测等。

**Q: 需要 API Key 吗？**  
A: 基础功能不需要。AI 策略生成功能需要 OpenAI API Key。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
