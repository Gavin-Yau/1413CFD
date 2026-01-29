"""
Data Management Utilities
Handles backfilling, data correction, and data integrity
"""
from typing import List, Dict, Optional
from datetime import datetime
import uuid
from models import Order, Transaction, Position, Account, OrderStatus, OrderSide
from services.trading_service import TradingDataService


class DataManagementService:
    """Service for data backfilling and correction"""
    
    def __init__(self, trading_service: TradingDataService):
        self.trading_service = trading_service
        self.correction_log = []
    
    def backfill_order(self, order_data: Dict) -> Order:
        """
        Backfill historical order data
        
        Args:
            order_data: Dictionary containing order information
            
        Returns:
            Created order object
        """
        # Validate required fields
        required_fields = ['customer_id', 'instrument', 'instrument_type', 
                          'order_type', 'side', 'quantity']
        for field in required_fields:
            if field not in order_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate order_id if not provided
        if 'order_id' not in order_data:
            order_data['order_id'] = str(uuid.uuid4())
        
        # Set default values
        if 'status' not in order_data:
            order_data['status'] = OrderStatus.FILLED
        if 'leverage' not in order_data:
            order_data['leverage'] = 1.0
        if 'commission' not in order_data:
            order_data['commission'] = 0.0
        if 'filled_quantity' not in order_data:
            order_data['filled_quantity'] = order_data['quantity']
        if 'created_at' not in order_data:
            order_data['created_at'] = datetime.now()
        if 'updated_at' not in order_data:
            order_data['updated_at'] = datetime.now()
        
        # Create order
        order = Order(**order_data)
        self.trading_service.orders[order.order_id] = order
        
        # Log backfill
        self._log_operation(
            operation_type="backfill_order",
            entity_id=order.order_id,
            details=f"Backfilled order for {order.instrument}",
            data=order_data
        )
        
        return order
    
    def backfill_transaction(self, transaction_data: Dict) -> Transaction:
        """
        Backfill historical transaction data
        
        Args:
            transaction_data: Dictionary containing transaction information
            
        Returns:
            Created transaction object
        """
        # Validate required fields
        required_fields = ['customer_id', 'order_id', 'instrument', 
                          'transaction_type', 'quantity', 'price', 'amount']
        for field in required_fields:
            if field not in transaction_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate transaction_id if not provided
        if 'transaction_id' not in transaction_data:
            transaction_data['transaction_id'] = str(uuid.uuid4())
        
        # Set default values
        if 'commission' not in transaction_data:
            transaction_data['commission'] = 0.0
        if 'pnl' not in transaction_data:
            transaction_data['pnl'] = 0.0
        if 'balance_after' not in transaction_data:
            transaction_data['balance_after'] = 0.0
        if 'timestamp' not in transaction_data:
            transaction_data['timestamp'] = datetime.now()
        
        # Create transaction
        transaction = Transaction(**transaction_data)
        self.trading_service.transactions[transaction.transaction_id] = transaction
        
        # Update account if exists
        account = self.trading_service.accounts.get(transaction.customer_id)
        if account:
            account.balance = transaction.balance_after
            if transaction.transaction_type == "close_position":
                account.total_trades += 1
                account.realized_pnl += transaction.pnl
                if transaction.pnl > 0:
                    account.winning_trades += 1
                elif transaction.pnl < 0:
                    account.losing_trades += 1
        
        # Log backfill
        self._log_operation(
            operation_type="backfill_transaction",
            entity_id=transaction.transaction_id,
            details=f"Backfilled transaction for {transaction.instrument}",
            data=transaction_data
        )
        
        return transaction
    
    def correct_order(self, order_id: str, corrections: Dict) -> Order:
        """
        Correct existing order data
        
        Args:
            order_id: Order ID to correct
            corrections: Dictionary of fields to correct
            
        Returns:
            Corrected order object
        """
        order = self.trading_service.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Store original values
        original_values = {}
        for field, new_value in corrections.items():
            if hasattr(order, field):
                original_values[field] = getattr(order, field)
                setattr(order, field, new_value)
        
        order.updated_at = datetime.now()
        
        # Log correction
        self._log_operation(
            operation_type="correct_order",
            entity_id=order_id,
            details=f"Corrected order fields: {list(corrections.keys())}",
            data={
                'original': original_values,
                'corrected': corrections
            }
        )
        
        return order
    
    def correct_transaction(self, transaction_id: str, corrections: Dict) -> Transaction:
        """
        Correct existing transaction data
        
        Args:
            transaction_id: Transaction ID to correct
            corrections: Dictionary of fields to correct
            
        Returns:
            Corrected transaction object
        """
        transaction = self.trading_service.transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        # Store original values
        original_values = {}
        for field, new_value in corrections.items():
            if hasattr(transaction, field):
                original_values[field] = getattr(transaction, field)
                setattr(transaction, field, new_value)
        
        # Log correction
        self._log_operation(
            operation_type="correct_transaction",
            entity_id=transaction_id,
            details=f"Corrected transaction fields: {list(corrections.keys())}",
            data={
                'original': original_values,
                'corrected': corrections
            }
        )
        
        return transaction
    
    def recalculate_account_statistics(self, customer_id: str) -> Account:
        """
        Recalculate account statistics from transactions
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Updated account object
        """
        account = self.trading_service.accounts.get(customer_id)
        if not account:
            raise ValueError(f"Account {customer_id} not found")
        
        # Get all transactions
        transactions = [
            tx for tx in self.trading_service.transactions.values()
            if tx.customer_id == customer_id
        ]
        
        # Recalculate statistics
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        realized_pnl = 0.0
        
        for tx in transactions:
            if tx.transaction_type == "close_position":
                total_trades += 1
                realized_pnl += tx.pnl
                if tx.pnl > 0:
                    winning_trades += 1
                elif tx.pnl < 0:
                    losing_trades += 1
        
        # Update account
        original_stats = {
            'total_trades': account.total_trades,
            'winning_trades': account.winning_trades,
            'losing_trades': account.losing_trades,
            'realized_pnl': account.realized_pnl
        }
        
        account.total_trades = total_trades
        account.winning_trades = winning_trades
        account.losing_trades = losing_trades
        account.realized_pnl = realized_pnl
        account.updated_at = datetime.now()
        
        # Log recalculation
        self._log_operation(
            operation_type="recalculate_statistics",
            entity_id=customer_id,
            details=f"Recalculated account statistics",
            data={
                'original': original_stats,
                'recalculated': {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'realized_pnl': realized_pnl
                }
            }
        )
        
        return account
    
    def delete_order(self, order_id: str, reason: str) -> bool:
        """
        Delete an order (with logging)
        
        Args:
            order_id: Order ID to delete
            reason: Reason for deletion
            
        Returns:
            True if deleted successfully
        """
        order = self.trading_service.orders.get(order_id)
        if not order:
            return False
        
        # Log deletion
        self._log_operation(
            operation_type="delete_order",
            entity_id=order_id,
            details=f"Deleted order: {reason}",
            data={'order': order.dict()}
        )
        
        # Delete order
        del self.trading_service.orders[order_id]
        return True
    
    def delete_transaction(self, transaction_id: str, reason: str) -> bool:
        """
        Delete a transaction (with logging)
        
        Args:
            transaction_id: Transaction ID to delete
            reason: Reason for deletion
            
        Returns:
            True if deleted successfully
        """
        transaction = self.trading_service.transactions.get(transaction_id)
        if not transaction:
            return False
        
        # Log deletion
        self._log_operation(
            operation_type="delete_transaction",
            entity_id=transaction_id,
            details=f"Deleted transaction: {reason}",
            data={'transaction': transaction.dict()}
        )
        
        # Delete transaction
        del self.trading_service.transactions[transaction_id]
        return True
    
    def bulk_import_orders(self, orders_data: List[Dict]) -> Dict:
        """
        Bulk import orders
        
        Args:
            orders_data: List of order dictionaries
            
        Returns:
            Dictionary with import results
        """
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for order_data in orders_data:
            try:
                self.backfill_order(order_data)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'order_data': order_data,
                    'error': str(e)
                })
        
        return results
    
    def bulk_import_transactions(self, transactions_data: List[Dict]) -> Dict:
        """
        Bulk import transactions
        
        Args:
            transactions_data: List of transaction dictionaries
            
        Returns:
            Dictionary with import results
        """
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for tx_data in transactions_data:
            try:
                self.backfill_transaction(tx_data)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'transaction_data': tx_data,
                    'error': str(e)
                })
        
        return results
    
    def get_correction_log(self, entity_id: Optional[str] = None) -> List[Dict]:
        """
        Get correction log
        
        Args:
            entity_id: Optional entity ID to filter by
            
        Returns:
            List of correction log entries
        """
        if entity_id:
            return [
                entry for entry in self.correction_log
                if entry['entity_id'] == entity_id
            ]
        return self.correction_log
    
    def _log_operation(self, operation_type: str, entity_id: str, 
                      details: str, data: Optional[Dict] = None):
        """Log data management operation"""
        log_entry = {
            'timestamp': datetime.now(),
            'operation_type': operation_type,
            'entity_id': entity_id,
            'details': details,
            'data': data
        }
        self.correction_log.append(log_entry)
