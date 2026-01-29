"""
Main CFD Backend System Application
Integrates all services and provides API interface
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from models import Account, Order, Position, Alert, Report
from services.nlp_service import OrderNLPParser
from services.risk_service import RiskControlService
from services.trading_service import TradingDataService
from services.report_service import ReportService
from services.notification_service import NotificationService
from services.data_management_service import DataManagementService
from config import Config


class CFDBackendSystem:
    """Main CFD Backend System"""
    
    def __init__(self):
        """Initialize all services"""
        self.nlp_parser = OrderNLPParser()
        self.risk_service = RiskControlService()
        self.trading_service = TradingDataService()
        self.report_service = ReportService(self.trading_service)
        self.notification_service = NotificationService()
        self.data_management = DataManagementService(self.trading_service)
        
        print("CFD Backend System Initialized")
        print("=" * 60)
    
    def create_account(self, customer_id: str, customer_name: str, 
                      initial_balance: float) -> Account:
        """
        Create a new customer account
        
        Args:
            customer_id: Customer identifier
            customer_name: Customer name
            initial_balance: Initial account balance
            
        Returns:
            Created account object
        """
        account = Account(
            account_id=str(uuid.uuid4()),
            customer_id=customer_id,
            customer_name=customer_name,
            balance=initial_balance,
            equity=initial_balance,
            margin_available=initial_balance,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.trading_service.accounts[customer_id] = account
        print(f"✓ Created account for {customer_name} (ID: {customer_id})")
        print(f"  Initial balance: {initial_balance:.2f}")
        
        return account
    
    def process_natural_language_order(self, instruction: str, 
                                      customer_id: str) -> Optional[Order]:
        """
        Process natural language order instruction
        
        Args:
            instruction: Natural language order instruction
            customer_id: Customer ID
            
        Returns:
            Created order if successful, None otherwise
        """
        print(f"\n📝 Processing order instruction: '{instruction}'")
        
        # Parse instruction
        order_data = self.nlp_parser.parse_order_instruction(instruction, customer_id)
        
        if not order_data:
            print("❌ Failed to parse order instruction")
            return None
        
        # Validate order
        is_valid, error_msg = self.nlp_parser.validate_order(order_data)
        if not is_valid:
            print(f"❌ Order validation failed: {error_msg}")
            return None
        
        # Create order
        order = Order(**order_data)
        
        # Generate confirmation
        confirmation = self.nlp_parser.generate_confirmation_message(order_data)
        print("\n" + confirmation)
        
        # Risk check before creating order
        account = self.trading_service.accounts.get(customer_id)
        if account:
            can_open, reason = self.risk_service.can_open_position(
                account, order.instrument, order.quantity, 
                order.price or 100.0, order.leverage  # Use dummy price if not specified
            )
            
            if not can_open:
                print(f"❌ Risk check failed: {reason}")
                return None
        
        # Store order
        self.trading_service.create_order(order)
        print(f"✓ Order created successfully (ID: {order.order_id})")
        
        return order
    
    def execute_order(self, order_id: str, execution_price: float):
        """
        Execute an order
        
        Args:
            order_id: Order ID
            execution_price: Execution price
        """
        print(f"\n⚡ Executing order {order_id} at price {execution_price}")
        
        try:
            transaction = self.trading_service.execute_order(order_id, execution_price)
            print(f"✓ Order executed successfully")
            print(f"  Transaction ID: {transaction.transaction_id}")
            print(f"  Quantity: {transaction.quantity}")
            print(f"  Price: {transaction.price:.4f}")
            print(f"  Commission: {transaction.commission:.2f}")
            
            # Check for risk alerts
            self._check_and_send_alerts(transaction.customer_id)
            
            return transaction
        except Exception as e:
            print(f"❌ Failed to execute order: {e}")
            return None
    
    def close_position(self, position_id: str, close_price: float):
        """
        Close a position
        
        Args:
            position_id: Position ID
            close_price: Closing price
        """
        print(f"\n🔒 Closing position {position_id} at price {close_price}")
        
        try:
            # Get position before closing
            position = self.trading_service.positions.get(position_id)
            if not position:
                print(f"❌ Position {position_id} not found")
                return None
            
            transaction = self.trading_service.close_position(position_id, close_price)
            print(f"✓ Position closed successfully")
            print(f"  P&L: {transaction.pnl:.2f}")
            print(f"  Commission: {transaction.commission:.2f}")
            print(f"  Net P&L: {transaction.pnl:.2f}")
            
            # Send notification
            self.notification_service.send_position_closed_notification(
                transaction.customer_id, transaction.instrument, transaction.pnl
            )
            
            # Check for risk alerts
            self._check_and_send_alerts(transaction.customer_id)
            
            return transaction
        except Exception as e:
            print(f"❌ Failed to close position: {e}")
            return None
    
    def update_market_prices(self, prices: Dict[str, float]):
        """
        Update market prices and recalculate positions
        
        Args:
            prices: Dictionary of instrument -> price
        """
        print(f"\n📊 Updating market prices for {len(prices)} instruments")
        
        # Update all positions
        for position in list(self.trading_service.positions.values()):
            if position.instrument in prices:
                new_price = prices[position.instrument]
                self.risk_service.update_position_pnl(position, new_price)
        
        # Update account equities
        for customer_id, account in self.trading_service.accounts.items():
            equity = self.trading_service.calculate_account_equity(customer_id, prices)
            account.equity = equity
            
            # Update margin level
            if account.margin_used > 0:
                account.margin_level = (equity / account.margin_used) * 100
            
            # Check for alerts
            self._check_and_send_alerts(customer_id)
        
        print("✓ Market prices updated")
    
    def generate_daily_report(self, customer_id: Optional[str] = None):
        """Generate daily report"""
        print(f"\n📈 Generating daily report...")
        
        report = self.report_service.generate_daily_report(customer_id=customer_id)
        self.notification_service.send_report_notification(report)
        
        return report
    
    def generate_weekly_report(self, customer_id: Optional[str] = None):
        """Generate weekly report"""
        print(f"\n📈 Generating weekly report...")
        
        report = self.report_service.generate_weekly_report(customer_id=customer_id)
        self.notification_service.send_report_notification(report)
        
        return report
    
    def generate_monthly_report(self, customer_id: Optional[str] = None):
        """Generate monthly report"""
        print(f"\n📈 Generating monthly report...")
        
        report = self.report_service.generate_monthly_report(customer_id=customer_id)
        self.notification_service.send_report_notification(report)
        
        return report
    
    def generate_customer_analysis(self, customer_id: str):
        """Generate customer-specific analysis"""
        print(f"\n🔍 Generating customer analysis for {customer_id}...")
        
        analysis = self.report_service.generate_customer_analysis_report(customer_id)
        
        print("\n客户分析报告 (Customer Analysis Report)")
        print("=" * 60)
        print(f"客户ID: {analysis['customer_id']}")
        print(f"\n交易统计 (Trading Statistics):")
        stats = analysis['trading_statistics']
        print(f"  总交易数: {stats['total_trades']}")
        print(f"  胜率: {stats['win_rate']:.2f}%")
        print(f"  总盈亏: {stats['total_pnl']:.2f}")
        print(f"\n交易模式 (Trading Patterns):")
        patterns = analysis['trading_patterns']
        print(f"  最常交易品种: {patterns['most_traded_instrument']}")
        print(f"  交易频率: {patterns['trading_frequency']}")
        print(f"  偏好交易时段: {patterns['preferred_trading_hours']}")
        
        return analysis
    
    def get_account_status(self, customer_id: str):
        """Get account status with risk assessment"""
        account = self.trading_service.accounts.get(customer_id)
        if not account:
            print(f"❌ Account {customer_id} not found")
            return None
        
        positions = self.trading_service.get_customer_positions(customer_id)
        risk_score = self.risk_service.get_account_risk_score(account)
        
        print(f"\n💼 Account Status for {account.customer_name}")
        print("=" * 60)
        print(f"Balance: {account.balance:.2f}")
        print(f"Equity: {account.equity:.2f}")
        print(f"Margin Used: {account.margin_used:.2f}")
        print(f"Margin Available: {account.margin_available:.2f}")
        print(f"Margin Level: {account.margin_level:.2f}%")
        print(f"Unrealized P&L: {account.unrealized_pnl:.2f}")
        print(f"Realized P&L: {account.realized_pnl:.2f}")
        print(f"Open Positions: {len(positions)}")
        print(f"Risk Score: {risk_score:.1f}/100")
        print("=" * 60)
        
        return {
            'account': account,
            'positions': positions,
            'risk_score': risk_score
        }
    
    def _check_and_send_alerts(self, customer_id: str):
        """Check for risk alerts and send notifications"""
        account = self.trading_service.accounts.get(customer_id)
        if not account:
            return
        
        positions = self.trading_service.get_customer_positions(customer_id)
        
        # Check position-level risks
        for position in positions:
            alerts = self.risk_service.check_position_risk(position)
            for alert in alerts:
                self.notification_service.send_alert(alert)
        
        # Check account-level risks
        account_alerts = self.risk_service.check_account_risk(account, positions)
        for alert in account_alerts:
            self.notification_service.send_alert(alert)


def main():
    """Main entry point for demonstration"""
    print("\n" + "=" * 60)
    print("CFD交易后台系统 (CFD Trading Backend System)")
    print("=" * 60)
    
    # Initialize system
    system = CFDBackendSystem()
    
    # Demo: Create account
    account = system.create_account(
        customer_id="C001",
        customer_name="张三 (Zhang San)",
        initial_balance=100000.0
    )
    
    # Demo: Process natural language orders
    print("\n" + "=" * 60)
    print("自然语言订单处理演示 (NLP Order Processing Demo)")
    print("=" * 60)
    
    # Chinese order
    order1 = system.process_natural_language_order(
        "买入 EURUSD 外汇 2手 杠杆10倍",
        "C001"
    )
    
    if order1:
        system.execute_order(order1.order_id, 1.0850)
    
    # English order
    order2 = system.process_natural_language_order(
        "buy 1 lot gold at 2000 leverage 5x",
        "C001"
    )
    
    if order2:
        system.execute_order(order2.order_id, 2000.0)
    
    # Demo: Update market prices
    system.update_market_prices({
        'EURUSD': 1.0900,  # Profit
        'GOLD': 1950.0      # Loss
    })
    
    # Demo: Get account status
    system.get_account_status("C001")
    
    # Demo: Generate reports
    system.generate_daily_report(customer_id="C001")
    
    # Demo: Customer analysis
    system.generate_customer_analysis("C001")
    
    print("\n" + "=" * 60)
    print("系统演示完成 (System Demo Complete)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
