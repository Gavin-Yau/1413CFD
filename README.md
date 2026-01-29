# CFD交易后台系统 (CFD Trading Backend System)

一个全面的CFD交易后台记账、分析、统计和通知系统。

A comprehensive backend accounting, analysis, statistics, and notification system for CFD trading.

## 功能特性 (Features)

### 1. 自然语言处理 (Natural Language Processing)
- 支持中文和英文交易指令
- 自动识别交易方向（买入/卖出）
- 解析交易品种、数量、价格、杠杆等参数
- 订单验证和确认消息生成

### 2. 智能风控和预警 (Intelligent Risk Control & Early Warning)
- 实时风险监控
- 保证金水平检查
- 追加保证金通知
- 强制平仓预警
- 持仓风险评分
- 账户风险评分

### 3. 实盘数据盈亏计算 (P&L Calculation)
- 实时持仓盈亏计算
- 已实现盈亏统计
- 浮动盈亏追踪
- 佣金费用计算
- 账户净值计算

### 4. 订单记录管理 (Order Record Management)
- 完整的订单生命周期管理
- 交易记录存储
- 持仓管理
- 交易历史查询

### 5. 报表生成 (Report Generation)
- 每日交易报表
- 每周交易报表
- 每月交易报表
- 客户分析报告
- 交易模式分析

### 6. 客户分析 (Customer Analysis)
- 交易统计分析
- 交易模式识别
- 风险指标计算
- 绩效评估

### 7. 数据管理 (Data Management)
- 历史数据补录
- 数据修正功能
- 批量导入
- 修正日志记录

### 8. 通知系统 (Notification System)
- 多渠道通知（控制台、文件、Telegram、短信）
- 风险预警通知
- 报表生成通知
- 平仓通知

## 系统架构 (System Architecture)

```
CFD Backend System
├── models/                 # 数据模型 (Data Models)
│   └── __init__.py        # Order, Position, Transaction, Account, Alert, Report
├── services/              # 业务服务 (Business Services)
│   ├── nlp_service.py    # 自然语言处理
│   ├── risk_service.py   # 风险控制
│   ├── trading_service.py # 交易数据处理
│   ├── report_service.py  # 报表生成
│   ├── notification_service.py # 通知服务
│   └── data_management_service.py # 数据管理
├── examples/              # 示例代码 (Examples)
│   ├── basic_trading.py
│   └── data_management.py
├── config.py              # 配置文件 (Configuration)
├── main.py               # 主程序 (Main Application)
└── requirements.txt      # 依赖包 (Dependencies)
```

## 安装说明 (Installation)

### 1. 环境要求 (Requirements)
- Python 3.8+
- pip

### 2. 安装依赖 (Install Dependencies)

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量 (Configure Environment Variables)

创建 `.env` 文件：

```bash
# Database
DATABASE_URL=sqlite:///cfd_system.db

# Risk Control Settings
MAX_POSITION_SIZE=100000
MAX_LEVERAGE=10
MARGIN_CALL_THRESHOLD=0.3
STOP_OUT_LEVEL=0.2

# Report Settings
REPORT_OUTPUT_DIR=./reports

# Notification Settings (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token

# Timezone
TIMEZONE=Asia/Shanghai
```

## 快速开始 (Quick Start)

### 运行主程序演示 (Run Main Demo)

```bash
python main.py
```

### 运行示例 (Run Examples)

```bash
# 基础交易流程
python examples/basic_trading.py

# 数据管理示例
python examples/data_management.py
```

## 使用指南 (Usage Guide)

### 1. 初始化系统 (Initialize System)

```python
from main import CFDBackendSystem

system = CFDBackendSystem()
```

### 2. 创建客户账户 (Create Customer Account)

```python
account = system.create_account(
    customer_id="C001",
    customer_name="Zhang San",
    initial_balance=100000.0
)
```

### 3. 使用自然语言下单 (Place Orders with Natural Language)

支持的指令格式：

```python
# 中文指令
system.process_natural_language_order(
    "买入 EURUSD 2手 杠杆10倍",
    "C001"
)

# 限价单
system.process_natural_language_order(
    "买入黄金 1手 价格 2050 杠杆5倍",
    "C001"
)

# English instructions
system.process_natural_language_order(
    "buy 1 lot EURUSD at 1.0850 leverage 5x",
    "C001"
)
```

### 4. 执行订单 (Execute Orders)

```python
transaction = system.execute_order(order_id, execution_price=1.0850)
```

### 5. 更新市场价格 (Update Market Prices)

```python
system.update_market_prices({
    'EURUSD': 1.0900,
    'GOLD': 2100.0
})
```

### 6. 平仓 (Close Positions)

```python
transaction = system.close_position(position_id, close_price=1.0900)
```

### 7. 生成报表 (Generate Reports)

```python
# 每日报表
daily_report = system.generate_daily_report(customer_id="C001")

# 每周报表
weekly_report = system.generate_weekly_report(customer_id="C001")

# 每月报表
monthly_report = system.generate_monthly_report(customer_id="C001")
```

### 8. 客户分析 (Customer Analysis)

```python
analysis = system.generate_customer_analysis("C001")
```

### 9. 查看账户状态 (Check Account Status)

```python
status = system.get_account_status("C001")
```

### 10. 数据管理 (Data Management)

```python
# 补录历史订单
order = system.data_management.backfill_order(order_data)

# 修正数据
corrected = system.data_management.correct_order(
    order_id, 
    {'commission': 12.0}
)

# 重新计算统计
system.data_management.recalculate_account_statistics(customer_id)
```

## 数据模型 (Data Models)

### Order (订单)
- order_id: 订单ID
- customer_id: 客户ID
- instrument: 交易品种
- order_type: 订单类型 (market/limit/stop)
- side: 交易方向 (buy/sell)
- quantity: 数量
- price: 价格
- leverage: 杠杆倍数
- status: 状态

### Position (持仓)
- position_id: 持仓ID
- customer_id: 客户ID
- instrument: 交易品种
- side: 方向 (buy/sell)
- quantity: 数量
- entry_price: 开仓价格
- current_price: 当前价格
- unrealized_pnl: 浮动盈亏
- leverage: 杠杆

### Transaction (交易记录)
- transaction_id: 交易ID
- customer_id: 客户ID
- order_id: 关联订单ID
- transaction_type: 交易类型
- quantity: 数量
- price: 价格
- pnl: 盈亏
- commission: 佣金

### Account (账户)
- account_id: 账户ID
- customer_id: 客户ID
- balance: 余额
- equity: 净值
- margin_used: 已用保证金
- margin_available: 可用保证金
- unrealized_pnl: 浮动盈亏
- realized_pnl: 已实现盈亏

## API参考 (API Reference)

详细的API文档请参考各个服务模块的源代码注释。

## 风险控制参数 (Risk Control Parameters)

系统提供以下风险控制参数（可在 `config.py` 中配置）：

- `MAX_POSITION_SIZE`: 最大持仓规模
- `MAX_LEVERAGE`: 最大杠杆倍数
- `MARGIN_CALL_THRESHOLD`: 保证金追加阈值 (默认30%)
- `STOP_OUT_LEVEL`: 强制平仓水平 (默认20%)
- `PROFIT_ALERT_THRESHOLD`: 盈利提醒阈值
- `LOSS_ALERT_THRESHOLD`: 亏损预警阈值

## 报表说明 (Reports)

### 生成的报表文件
- CSV格式报表保存在 `./reports/` 目录
- 包含汇总报表和详细交易记录
- 支持按客户或系统级别生成

### 报表内容
- 交易统计（总交易数、胜率、盈亏）
- 最大盈利/亏损
- 平均盈利/亏损
- 盈亏比（Profit Factor）
- 详细交易记录

## 日志和通知 (Logs and Notifications)

### 日志文件
- 通知日志保存在 `./logs/` 目录
- 按日期分文件记录
- 包含所有告警和通知历史

### 通知渠道
1. **控制台**: 实时输出
2. **文件日志**: 持久化记录
3. **Telegram**: 即时消息通知（需配置）
4. **短信**: SMS通知（需配置）

## 扩展开发 (Extension Development)

### 添加新的交易品种
在 `models/__init__.py` 中扩展 `InstrumentType` 枚举。

### 自定义风险规则
在 `services/risk_service.py` 中添加新的风险检查方法。

### 添加新的报表类型
在 `services/report_service.py` 中实现新的报表生成方法。

### 集成外部数据源
在 `services/trading_service.py` 中添加数据接口。

## 性能优化 (Performance Optimization)

- 使用数据库代替内存存储（生产环境）
- 实现缓存机制
- 异步处理报表生成
- 批量处理交易数据

## 安全性 (Security)

- 不要在代码中硬编码敏感信息
- 使用环境变量配置API密钥
- 实施访问控制和身份验证
- 定期备份数据
- 加密敏感数据

## 贡献 (Contributing)

欢迎贡献代码、报告问题或提出改进建议。

## 许可证 (License)

MIT License

## 联系方式 (Contact)

如有问题或建议，请通过GitHub Issues联系。

---

**注意**: 本系统为演示和学习目的。在生产环境中使用前，请确保：
1. 实施完整的数据库持久化
2. 添加用户认证和授权
3. 实施完整的错误处理
4. 进行充分的测试
5. 遵守相关金融监管要求
