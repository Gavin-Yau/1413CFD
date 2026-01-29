"""
Example: Basic Trading Workflow
Demonstrates basic trading operations
"""
from main import CFDBackendSystem


def basic_trading_example():
    """Basic trading workflow example"""
    print("基础交易流程示例 (Basic Trading Workflow Example)")
    print("=" * 60)
    
    # Initialize system
    system = CFDBackendSystem()
    
    # Step 1: Create customer account
    print("\n1. 创建客户账户 (Create Customer Account)")
    account = system.create_account(
        customer_id="DEMO001",
        customer_name="Demo User",
        initial_balance=50000.0
    )
    
    # Step 2: Process orders using natural language
    print("\n2. 使用自然语言下单 (Place Orders with Natural Language)")
    
    orders_to_process = [
        "买入 EURUSD 1手 限价 1.0800 杠杆5倍",
        "卖出 GBPUSD 0.5手 市价单 杠杆3倍",
        "买入黄金 2手 价格 2050 杠杆10倍"
    ]
    
    order_ids = []
    for instruction in orders_to_process:
        order = system.process_natural_language_order(instruction, "DEMO001")
        if order:
            order_ids.append(order.order_id)
    
    # Step 3: Execute orders
    print("\n3. 执行订单 (Execute Orders)")
    execution_prices = {
        0: 1.0800,  # EURUSD
        1: 1.2650,  # GBPUSD
        2: 2050.0   # Gold
    }
    
    for idx, order_id in enumerate(order_ids):
        if idx in execution_prices:
            system.execute_order(order_id, execution_prices[idx])
    
    # Step 4: Update market prices
    print("\n4. 更新市场价格 (Update Market Prices)")
    system.update_market_prices({
        'EURUSD': 1.0850,  # +50 pips profit
        'GBPUSD': 1.2600,  # +50 pips profit (short)
        'GOLD': 2100.0     # +50 profit
    })
    
    # Step 5: Check account status
    print("\n5. 检查账户状态 (Check Account Status)")
    system.get_account_status("DEMO001")
    
    # Step 6: Close some positions
    print("\n6. 平仓部分持仓 (Close Some Positions)")
    positions = system.trading_service.get_customer_positions("DEMO001")
    if positions:
        # Close first position
        system.close_position(positions[0].position_id, 1.0860)
    
    # Step 7: Generate reports
    print("\n7. 生成报表 (Generate Reports)")
    system.generate_daily_report(customer_id="DEMO001")
    system.generate_customer_analysis("DEMO001")
    
    print("\n✓ 基础交易流程示例完成 (Basic Trading Example Complete)")


if __name__ == "__main__":
    basic_trading_example()
