"""
Example: Data Backfill and Correction
Demonstrates data management features
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CFDBackendSystem
from datetime import datetime, timedelta


def data_management_example():
    """Data backfill and correction example"""
    print("数据补录和修正示例 (Data Backfill and Correction Example)")
    print("=" * 60)
    
    # Initialize system
    system = CFDBackendSystem()
    
    # Create account
    account = system.create_account(
        customer_id="DATA001",
        customer_name="Data Demo User",
        initial_balance=100000.0
    )
    
    # Example 1: Backfill historical orders
    print("\n1. 补录历史订单 (Backfill Historical Orders)")
    
    historical_orders = [
        {
            'customer_id': 'DATA001',
            'instrument': 'EURUSD',
            'instrument_type': 'forex',
            'order_type': 'market',
            'side': 'buy',
            'quantity': 1.0,
            'leverage': 5.0,
            'status': 'filled',
            'filled_quantity': 1.0,
            'average_fill_price': 1.0750,
            'commission': 10.75,
            'created_at': datetime.now() - timedelta(days=7)
        },
        {
            'customer_id': 'DATA001',
            'instrument': 'GOLD',
            'instrument_type': 'commodity',
            'order_type': 'limit',
            'side': 'buy',
            'quantity': 2.0,
            'price': 2000.0,
            'leverage': 10.0,
            'status': 'filled',
            'filled_quantity': 2.0,
            'average_fill_price': 2000.0,
            'commission': 40.0,
            'created_at': datetime.now() - timedelta(days=5)
        }
    ]
    
    for order_data in historical_orders:
        order = system.data_management.backfill_order(order_data)
        print(f"  ✓ Backfilled order: {order.instrument} ({order.order_id})")
    
    # Example 2: Backfill transactions
    print("\n2. 补录交易记录 (Backfill Transactions)")
    
    historical_transactions = [
        {
            'customer_id': 'DATA001',
            'order_id': 'HIST001',
            'instrument': 'EURUSD',
            'transaction_type': 'close_position',
            'quantity': 1.0,
            'price': 1.0800,
            'amount': 108000.0,
            'commission': 10.8,
            'pnl': 50.0,
            'balance_after': 100039.2,
            'timestamp': datetime.now() - timedelta(days=3)
        }
    ]
    
    for tx_data in historical_transactions:
        tx = system.data_management.backfill_transaction(tx_data)
        print(f"  ✓ Backfilled transaction: {tx.instrument} ({tx.transaction_id})")
    
    # Example 3: Correct order data
    print("\n3. 修正订单数据 (Correct Order Data)")
    
    orders = list(system.trading_service.orders.values())
    if orders:
        order_to_correct = orders[0]
        print(f"  Original commission: {order_to_correct.commission}")
        
        corrected = system.data_management.correct_order(
            order_to_correct.order_id,
            {'commission': 12.0, 'notes': 'Commission corrected'}
        )
        print(f"  Corrected commission: {corrected.commission}")
    
    # Example 4: Recalculate account statistics
    print("\n4. 重新计算账户统计 (Recalculate Account Statistics)")
    
    print(f"  Before: Total trades = {account.total_trades}")
    recalculated = system.data_management.recalculate_account_statistics('DATA001')
    print(f"  After: Total trades = {recalculated.total_trades}")
    
    # Example 5: View correction log
    print("\n5. 查看修正日志 (View Correction Log)")
    
    log = system.data_management.get_correction_log()
    print(f"  Total corrections: {len(log)}")
    for entry in log[-3:]:  # Show last 3 entries
        print(f"  - {entry['operation_type']}: {entry['details']}")
    
    print("\n✓ 数据管理示例完成 (Data Management Example Complete)")


if __name__ == "__main__":
    data_management_example()
