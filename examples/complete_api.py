"""
Example: Complete API Usage
Demonstrates all major features of the system
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CFDBackendSystem
from datetime import datetime, timedelta


def complete_api_example():
    """Complete API usage demonstration"""
    print("\n" + "="*60)
    print("完整API使用示例 (Complete API Usage Example)")
    print("="*60)
    
    # Initialize system
    system = CFDBackendSystem()
    
    # ========== Account Management ==========
    print("\n1️⃣  账户管理 (Account Management)")
    print("-" * 60)
    
    # Create multiple accounts
    accounts = []
    for i in range(1, 4):
        account = system.create_account(
            customer_id=f"API{i:03d}",
            customer_name=f"API Test User {i}",
            initial_balance=50000.0 + i * 10000
        )
        accounts.append(account)
    
    # ========== Natural Language Order Processing ==========
    print("\n2️⃣  自然语言订单处理 (Natural Language Order Processing)")
    print("-" * 60)
    
    # Various order instructions
    instructions = [
        ("API001", "买入 EURUSD 1手 杠杆5倍"),
        ("API001", "买入黄金 0.5手 价格 2050 杠杆10倍"),
        ("API002", "sell 2 lots GBPUSD leverage 3x"),
        ("API002", "buy silver 1 lot at 25 leverage 5x"),
        ("API003", "买入 USDJPY 2手 市价单 杠杆8倍"),
    ]
    
    executed_orders = []
    for customer_id, instruction in instructions:
        print(f"\n客户 {customer_id}: {instruction}")
        order = system.process_natural_language_order(instruction, customer_id)
        if order:
            executed_orders.append((customer_id, order))
    
    # Execute all orders
    print("\n3️⃣  订单执行 (Order Execution)")
    print("-" * 60)
    
    execution_prices = {
        'EURUSD': 1.0850,
        'GOLD': 2050.0,
        'GBPUSD': 1.2650,
        'SILVER': 25.0,
        'USDJPY': 145.50
    }
    
    for customer_id, order in executed_orders:
        price = execution_prices.get(order.instrument, 100.0)
        system.execute_order(order.order_id, price)
    
    # ========== Market Price Updates ==========
    print("\n4️⃣  市场价格更新 (Market Price Updates)")
    print("-" * 60)
    
    # Simulate price movements
    system.update_market_prices({
        'EURUSD': 1.0900,   # +50 pips
        'GOLD': 2100.0,      # +50
        'GBPUSD': 1.2600,   # +50 pips (profit on short)
        'SILVER': 26.0,     # +1
        'USDJPY': 146.00    # +50 pips
    })
    
    # ========== Account Status Check ==========
    print("\n5️⃣  账户状态检查 (Account Status Check)")
    print("-" * 60)
    
    for account in accounts:
        status = system.get_account_status(account.customer_id)
        if status:
            print(f"\n账户 {account.customer_id}:")
            print(f"  持仓数量: {len(status['positions'])}")
            print(f"  风险评分: {status['risk_score']:.1f}/100")
    
    # ========== Risk Management ==========
    print("\n6️⃣  风险管理 (Risk Management)")
    print("-" * 60)
    
    # Get position risk scores
    for customer_id in ['API001', 'API002', 'API003']:
        positions = system.trading_service.get_customer_positions(customer_id)
        if positions:
            print(f"\n客户 {customer_id} 持仓风险:")
            for pos in positions:
                risk_score = system.risk_service.get_position_risk_score(pos)
                print(f"  {pos.instrument}: 风险评分 {risk_score:.1f}/100, "
                      f"浮盈亏 {pos.unrealized_pnl:.2f}")
    
    # ========== Position Closing ==========
    print("\n7️⃣  平仓操作 (Position Closing)")
    print("-" * 60)
    
    # Close some profitable positions
    for customer_id in ['API001', 'API002']:
        positions = system.trading_service.get_customer_positions(customer_id)
        if positions:
            position = positions[0]
            close_price = execution_prices.get(position.instrument, 100.0) * 1.01
            print(f"\n平仓 {customer_id} 的 {position.instrument} 持仓")
            system.close_position(position.position_id, close_price)
    
    # ========== Report Generation ==========
    print("\n8️⃣  报表生成 (Report Generation)")
    print("-" * 60)
    
    # Generate reports for each customer
    for customer_id in ['API001', 'API002', 'API003']:
        print(f"\n生成 {customer_id} 的每日报表...")
        report = system.generate_daily_report(customer_id=customer_id)
        print(f"  报表文件: {report.file_path}")
        print(f"  总交易: {report.total_trades}, 胜率: {report.win_rate:.1f}%")
    
    # Generate system-wide report
    print("\n生成系统全局报表...")
    system_report = system.generate_daily_report()
    print(f"  系统总交易: {system_report.total_trades}")
    print(f"  系统总盈亏: {system_report.total_pnl:.2f}")
    
    # ========== Customer Analysis ==========
    print("\n9️⃣  客户分析 (Customer Analysis)")
    print("-" * 60)
    
    for customer_id in ['API001', 'API002']:
        print(f"\n分析客户 {customer_id}...")
        analysis = system.generate_customer_analysis(customer_id)
        patterns = analysis['trading_patterns']
        print(f"  最常交易品种: {patterns['most_traded_instrument']}")
        print(f"  交易频率: {patterns['trading_frequency']}")
        print(f"  平均交易规模: {patterns['average_trade_size']:.2f}")
    
    # ========== Data Management ==========
    print("\n🔟 数据管理 (Data Management)")
    print("-" * 60)
    
    # Backfill a historical order
    print("\n补录历史订单...")
    historical_order = {
        'customer_id': 'API001',
        'instrument': 'BTCUSD',
        'instrument_type': 'crypto',
        'order_type': 'market',
        'side': 'buy',
        'quantity': 0.1,
        'leverage': 2.0,
        'status': 'filled',
        'filled_quantity': 0.1,
        'average_fill_price': 50000.0,
        'commission': 5.0,
        'created_at': datetime.now() - timedelta(days=7)
    }
    backfilled = system.data_management.backfill_order(historical_order)
    print(f"  ✓ 补录订单: {backfilled.instrument} (ID: {backfilled.order_id})")
    
    # View correction log
    print("\n查看数据修正日志...")
    log = system.data_management.get_correction_log()
    print(f"  总修正次数: {len(log)}")
    if log:
        print(f"  最近一次: {log[-1]['operation_type']} - {log[-1]['details']}")
    
    # ========== Summary ==========
    print("\n" + "="*60)
    print("📊 系统摘要 (System Summary)")
    print("="*60)
    
    total_accounts = len(system.trading_service.accounts)
    total_orders = len(system.trading_service.orders)
    total_positions = len(system.trading_service.positions)
    total_transactions = len(system.trading_service.transactions)
    
    print(f"总账户数: {total_accounts}")
    print(f"总订单数: {total_orders}")
    print(f"活跃持仓: {total_positions}")
    print(f"总交易记录: {total_transactions}")
    
    print("\n✅ 完整API示例执行完成 (Complete API Example Finished)")
    print("="*60 + "\n")


if __name__ == "__main__":
    complete_api_example()
