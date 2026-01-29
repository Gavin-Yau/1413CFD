"""
Trading Data Processing and P&L Calculation Service
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import Order, Position, Transaction, Account, OrderSide, OrderStatus
import uuid


class TradingDataService:
    """Service for processing trading data and calculating P&L"""
    
    def __init__(self):
        # In-memory storage (in production, this would be a database)
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.accounts: Dict[str, Account] = {}
    
    def create_order(self, order: Order) -> Order:
        """Create and store a new order"""
        self.orders[order.order_id] = order
        return order
    
    def execute_order(self, order_id: str, execution_price: float, 
                     execution_quantity: Optional[float] = None) -> Transaction:
        """
        Execute an order and create corresponding position/transaction
        
        Args:
            order_id: Order ID to execute
            execution_price: Execution price
            execution_quantity: Quantity executed (None = full order)
            
        Returns:
            Transaction record
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]:
            raise ValueError(f"Order {order_id} cannot be executed (status: {order.status})")
        
        # Determine execution quantity
        if execution_quantity is None:
            execution_quantity = order.quantity - order.filled_quantity
        
        # Calculate commission (0.1% of trade value)
        trade_value = execution_quantity * execution_price
        commission = trade_value * 0.001
        
        # Update order
        order.filled_quantity += execution_quantity
        order.average_fill_price = (
            (order.average_fill_price or 0) * (order.filled_quantity - execution_quantity) +
            execution_price * execution_quantity
        ) / order.filled_quantity
        order.commission += commission
        order.updated_at = datetime.now()
        
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED
        
        # Create or update position
        position = self._create_or_update_position(order, execution_quantity, execution_price)
        
        # Create transaction record
        transaction = self._create_transaction(
            order=order,
            position=position,
            quantity=execution_quantity,
            price=execution_price,
            commission=commission
        )
        
        # Update account
        self._update_account_after_trade(order.customer_id, transaction)
        
        return transaction
    
    def close_position(self, position_id: str, close_price: float, 
                      close_quantity: Optional[float] = None) -> Transaction:
        """
        Close a position (fully or partially)
        
        Args:
            position_id: Position ID to close
            close_price: Closing price
            close_quantity: Quantity to close (None = full position)
            
        Returns:
            Transaction record
        """
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Determine close quantity
        if close_quantity is None:
            close_quantity = position.quantity
        
        if close_quantity > position.quantity:
            raise ValueError(f"Close quantity {close_quantity} exceeds position quantity {position.quantity}")
        
        # Calculate P&L
        if position.side == OrderSide.BUY:
            pnl = (close_price - position.entry_price) * close_quantity
        else:
            pnl = (position.entry_price - close_price) * close_quantity
        
        # Calculate commission
        trade_value = close_quantity * close_price
        commission = trade_value * 0.001
        
        # Net P&L
        net_pnl = pnl - commission
        
        # Update position
        position.realized_pnl += net_pnl
        position.quantity -= close_quantity
        position.updated_at = datetime.now()
        
        # Create closing transaction
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            customer_id=position.customer_id,
            order_id="CLOSE_" + position_id,
            position_id=position_id,
            instrument=position.instrument,
            transaction_type="close_position",
            quantity=close_quantity,
            price=close_price,
            amount=trade_value,
            commission=commission,
            pnl=net_pnl,
            balance_after=0.0,  # Will be updated
            timestamp=datetime.now()
        )
        
        self.transactions[transaction.transaction_id] = transaction
        
        # Update account
        self._update_account_after_trade(position.customer_id, transaction)
        
        # Remove position if fully closed
        if position.quantity <= 0:
            del self.positions[position_id]
        
        return transaction
    
    def calculate_account_equity(self, account_id: str, 
                                current_prices: Dict[str, float]) -> float:
        """
        Calculate account equity including unrealized P&L
        
        Args:
            account_id: Account ID
            current_prices: Dictionary of instrument -> current price
            
        Returns:
            Total account equity
        """
        account = self.accounts.get(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        # Start with balance
        equity = account.balance
        
        # Add unrealized P&L from open positions
        for position in self.positions.values():
            if position.customer_id == account.customer_id:
                current_price = current_prices.get(position.instrument)
                if current_price:
                    if position.side == OrderSide.BUY:
                        unrealized_pnl = (current_price - position.entry_price) * position.quantity
                    else:
                        unrealized_pnl = (position.entry_price - current_price) * position.quantity
                    
                    equity += unrealized_pnl
                    position.unrealized_pnl = unrealized_pnl
                    position.current_price = current_price
        
        return equity
    
    def get_customer_positions(self, customer_id: str) -> List[Position]:
        """Get all open positions for a customer"""
        return [
            pos for pos in self.positions.values()
            if pos.customer_id == customer_id
        ]
    
    def get_customer_orders(self, customer_id: str, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[Order]:
        """Get orders for a customer within date range"""
        orders = [
            order for order in self.orders.values()
            if order.customer_id == customer_id
        ]
        
        if start_date:
            orders = [o for o in orders if o.created_at >= start_date]
        if end_date:
            orders = [o for o in orders if o.created_at <= end_date]
        
        return sorted(orders, key=lambda x: x.created_at, reverse=True)
    
    def get_customer_transactions(self, customer_id: str,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> List[Transaction]:
        """Get transactions for a customer within date range"""
        transactions = [
            tx for tx in self.transactions.values()
            if tx.customer_id == customer_id
        ]
        
        if start_date:
            transactions = [t for t in transactions if t.timestamp >= start_date]
        if end_date:
            transactions = [t for t in transactions if t.timestamp <= end_date]
        
        return sorted(transactions, key=lambda x: x.timestamp, reverse=True)
    
    def calculate_trading_statistics(self, customer_id: str,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> Dict:
        """
        Calculate trading statistics for a customer
        
        Returns:
            Dictionary with trading statistics
        """
        transactions = self.get_customer_transactions(customer_id, start_date, end_date)
        
        if not transactions:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'total_commission': 0.0,
                'net_pnl': 0.0,
                'win_rate': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'profit_factor': 0.0
            }
        
        # Filter closing transactions
        closing_txs = [tx for tx in transactions if tx.transaction_type == "close_position"]
        
        total_trades = len(closing_txs)
        winning_trades = [tx for tx in closing_txs if tx.pnl > 0]
        losing_trades = [tx for tx in closing_txs if tx.pnl < 0]
        
        total_pnl = sum(tx.pnl for tx in closing_txs)
        total_commission = sum(tx.commission for tx in transactions)
        net_pnl = total_pnl
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0.0
        
        average_win = sum(tx.pnl for tx in winning_trades) / len(winning_trades) if winning_trades else 0.0
        average_loss = sum(tx.pnl for tx in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        largest_win = max((tx.pnl for tx in winning_trades), default=0.0)
        largest_loss = min((tx.pnl for tx in losing_trades), default=0.0)
        
        total_wins = sum(tx.pnl for tx in winning_trades)
        total_losses = abs(sum(tx.pnl for tx in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_pnl': total_pnl,
            'total_commission': total_commission,
            'net_pnl': net_pnl,
            'win_rate': win_rate,
            'average_win': average_win,
            'average_loss': average_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor
        }
    
    def _create_or_update_position(self, order: Order, quantity: float, 
                                  price: float) -> Position:
        """Create new position or update existing one"""
        # Find existing position with same instrument and side
        existing_position = None
        for pos in self.positions.values():
            if (pos.customer_id == order.customer_id and 
                pos.instrument == order.instrument and
                pos.side == order.side):
                existing_position = pos
                break
        
        if existing_position:
            # Update existing position (average price)
            total_quantity = existing_position.quantity + quantity
            avg_price = (
                existing_position.entry_price * existing_position.quantity +
                price * quantity
            ) / total_quantity
            
            existing_position.quantity = total_quantity
            existing_position.entry_price = avg_price
            existing_position.updated_at = datetime.now()
            
            # Update margin
            existing_position.margin_used = (
                total_quantity * avg_price / existing_position.leverage
            )
            
            return existing_position
        else:
            # Create new position
            position = Position(
                position_id=str(uuid.uuid4()),
                customer_id=order.customer_id,
                instrument=order.instrument,
                instrument_type=order.instrument_type,
                side=order.side,
                quantity=quantity,
                entry_price=price,
                leverage=order.leverage,
                margin_used=quantity * price / order.leverage,
                opened_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.positions[position.position_id] = position
            return position
    
    def _create_transaction(self, order: Order, position: Position,
                          quantity: float, price: float, commission: float) -> Transaction:
        """Create transaction record"""
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            customer_id=order.customer_id,
            order_id=order.order_id,
            position_id=position.position_id,
            instrument=order.instrument,
            transaction_type="open_position",
            quantity=quantity,
            price=price,
            amount=quantity * price,
            commission=commission,
            pnl=0.0,
            balance_after=0.0,  # Will be updated
            timestamp=datetime.now()
        )
        
        self.transactions[transaction.transaction_id] = transaction
        return transaction
    
    def _update_account_after_trade(self, customer_id: str, transaction: Transaction):
        """Update account after a trade"""
        account = self.accounts.get(customer_id)
        if account:
            # Update balance
            account.balance += transaction.pnl - transaction.commission
            transaction.balance_after = account.balance
            
            # Update statistics
            if transaction.transaction_type == "close_position":
                account.total_trades += 1
                account.realized_pnl += transaction.pnl
                
                if transaction.pnl > 0:
                    account.winning_trades += 1
                elif transaction.pnl < 0:
                    account.losing_trades += 1
            
            account.updated_at = datetime.now()
