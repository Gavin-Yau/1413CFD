"""
Report Generation Service
Generates daily, weekly, and monthly trading reports
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import os
import uuid
from models import Report
from services.trading_service import TradingDataService
from config import Config
import pandas as pd


class ReportService:
    """Service for generating trading reports"""
    
    def __init__(self, trading_service: TradingDataService):
        self.trading_service = trading_service
        self.output_dir = Config.REPORT_OUTPUT_DIR
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_daily_report(self, date: Optional[datetime] = None,
                            customer_id: Optional[str] = None) -> Report:
        """
        Generate daily trading report
        
        Args:
            date: Report date (default: today)
            customer_id: Customer ID (None for system-wide report)
            
        Returns:
            Report object
        """
        if date is None:
            date = datetime.now()
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        return self._generate_report(
            report_type="daily",
            start_date=start_date,
            end_date=end_date,
            customer_id=customer_id
        )
    
    def generate_weekly_report(self, date: Optional[datetime] = None,
                             customer_id: Optional[str] = None) -> Report:
        """
        Generate weekly trading report
        
        Args:
            date: Week reference date (default: current week)
            customer_id: Customer ID (None for system-wide report)
            
        Returns:
            Report object
        """
        if date is None:
            date = datetime.now()
        
        # Start of week (Monday)
        start_date = date - timedelta(days=date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        
        return self._generate_report(
            report_type="weekly",
            start_date=start_date,
            end_date=end_date,
            customer_id=customer_id
        )
    
    def generate_monthly_report(self, year: Optional[int] = None,
                              month: Optional[int] = None,
                              customer_id: Optional[str] = None) -> Report:
        """
        Generate monthly trading report
        
        Args:
            year: Year (default: current year)
            month: Month (default: current month)
            customer_id: Customer ID (None for system-wide report)
            
        Returns:
            Report object
        """
        now = datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        start_date = datetime(year, month, 1)
        
        # Calculate end date (first day of next month)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        return self._generate_report(
            report_type="monthly",
            start_date=start_date,
            end_date=end_date,
            customer_id=customer_id
        )
    
    def _generate_report(self, report_type: str, start_date: datetime,
                        end_date: datetime, customer_id: Optional[str] = None) -> Report:
        """
        Internal method to generate report
        
        Args:
            report_type: Type of report (daily/weekly/monthly)
            start_date: Report period start
            end_date: Report period end
            customer_id: Customer ID (None for system-wide)
            
        Returns:
            Report object
        """
        # Get trading statistics
        if customer_id:
            stats = self.trading_service.calculate_trading_statistics(
                customer_id, start_date, end_date
            )
            customers = [customer_id]
        else:
            # System-wide report: aggregate all customers
            stats = self._calculate_system_statistics(start_date, end_date)
            customers = list(self.trading_service.accounts.keys())
        
        # Create report object
        report = Report(
            report_id=str(uuid.uuid4()),
            report_type=report_type,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            total_trades=stats['total_trades'],
            total_pnl=stats['total_pnl'],
            winning_trades=stats['winning_trades'],
            losing_trades=stats['losing_trades'],
            total_commission=stats['total_commission'],
            largest_win=stats['largest_win'],
            largest_loss=stats['largest_loss'],
            average_win=stats['average_win'],
            average_loss=stats['average_loss'],
            win_rate=stats['win_rate'],
            profit_factor=stats['profit_factor'],
            generated_at=datetime.now()
        )
        
        # Generate report file
        file_path = self._generate_report_file(report, stats, customers)
        report.file_path = file_path
        
        return report
    
    def _calculate_system_statistics(self, start_date: datetime,
                                    end_date: datetime) -> Dict:
        """Calculate system-wide statistics"""
        all_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'total_commission': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'win_amounts': [],
            'loss_amounts': []
        }
        
        for customer_id in self.trading_service.accounts.keys():
            stats = self.trading_service.calculate_trading_statistics(
                customer_id, start_date, end_date
            )
            
            all_stats['total_trades'] += stats['total_trades']
            all_stats['winning_trades'] += stats['winning_trades']
            all_stats['losing_trades'] += stats['losing_trades']
            all_stats['total_pnl'] += stats['total_pnl']
            all_stats['total_commission'] += stats['total_commission']
            
            if stats['largest_win'] > all_stats['largest_win']:
                all_stats['largest_win'] = stats['largest_win']
            if stats['largest_loss'] < all_stats['largest_loss']:
                all_stats['largest_loss'] = stats['largest_loss']
            
            # Collect individual wins/losses for averaging
            transactions = self.trading_service.get_customer_transactions(
                customer_id, start_date, end_date
            )
            for tx in transactions:
                if tx.transaction_type == "close_position":
                    if tx.pnl > 0:
                        all_stats['win_amounts'].append(tx.pnl)
                    elif tx.pnl < 0:
                        all_stats['loss_amounts'].append(tx.pnl)
        
        # Calculate averages
        average_win = (sum(all_stats['win_amounts']) / len(all_stats['win_amounts'])
                      if all_stats['win_amounts'] else 0.0)
        average_loss = (sum(all_stats['loss_amounts']) / len(all_stats['loss_amounts'])
                       if all_stats['loss_amounts'] else 0.0)
        
        win_rate = (all_stats['winning_trades'] / all_stats['total_trades'] * 100
                   if all_stats['total_trades'] > 0 else 0.0)
        
        total_wins = sum(all_stats['win_amounts'])
        total_losses = abs(sum(all_stats['loss_amounts']))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        return {
            'total_trades': all_stats['total_trades'],
            'winning_trades': all_stats['winning_trades'],
            'losing_trades': all_stats['losing_trades'],
            'total_pnl': all_stats['total_pnl'],
            'total_commission': all_stats['total_commission'],
            'net_pnl': all_stats['total_pnl'],
            'largest_win': all_stats['largest_win'],
            'largest_loss': all_stats['largest_loss'],
            'average_win': average_win,
            'average_loss': average_loss,
            'win_rate': win_rate,
            'profit_factor': profit_factor
        }
    
    def _generate_report_file(self, report: Report, stats: Dict,
                            customers: List[str]) -> str:
        """
        Generate report file (CSV format)
        
        Returns:
            File path
        """
        # Prepare report data
        report_data = {
            'Report ID': [report.report_id],
            'Report Type': [report.report_type],
            'Period Start': [report.start_date.strftime('%Y-%m-%d %H:%M:%S')],
            'Period End': [report.end_date.strftime('%Y-%m-%d %H:%M:%S')],
            'Customer ID': [report.customer_id or 'System-wide'],
            'Total Trades': [report.total_trades],
            'Winning Trades': [report.winning_trades],
            'Losing Trades': [report.losing_trades],
            'Win Rate (%)': [f"{report.win_rate:.2f}"],
            'Total P&L': [f"{report.total_pnl:.2f}"],
            'Total Commission': [f"{report.total_commission:.2f}"],
            'Net P&L': [f"{report.total_pnl:.2f}"],
            'Largest Win': [f"{report.largest_win:.2f}"],
            'Largest Loss': [f"{report.largest_loss:.2f}"],
            'Average Win': [f"{report.average_win:.2f}"],
            'Average Loss': [f"{report.average_loss:.2f}"],
            'Profit Factor': [f"{report.profit_factor:.2f}"],
            'Generated At': [report.generated_at.strftime('%Y-%m-%d %H:%M:%S')]
        }
        
        df = pd.DataFrame(report_data)
        
        # Generate filename
        customer_str = report.customer_id or 'system'
        filename = f"{report.report_type}_{customer_str}_{report.start_date.strftime('%Y%m%d')}.csv"
        file_path = os.path.join(self.output_dir, filename)
        
        # Save to CSV
        df.to_csv(file_path, index=False)
        
        # Also generate detailed transaction report if customer-specific
        if report.customer_id:
            self._generate_detailed_transaction_report(
                report.customer_id, report.start_date, report.end_date, filename.replace('.csv', '_details.csv')
            )
        
        return file_path
    
    def _generate_detailed_transaction_report(self, customer_id: str,
                                            start_date: datetime,
                                            end_date: datetime,
                                            filename: str):
        """Generate detailed transaction report"""
        transactions = self.trading_service.get_customer_transactions(
            customer_id, start_date, end_date
        )
        
        if not transactions:
            return
        
        tx_data = []
        for tx in transactions:
            tx_data.append({
                'Transaction ID': tx.transaction_id,
                'Timestamp': tx.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Order ID': tx.order_id,
                'Position ID': tx.position_id or '',
                'Instrument': tx.instrument,
                'Type': tx.transaction_type,
                'Quantity': tx.quantity,
                'Price': f"{tx.price:.4f}",
                'Amount': f"{tx.amount:.2f}",
                'Commission': f"{tx.commission:.2f}",
                'P&L': f"{tx.pnl:.2f}",
                'Balance After': f"{tx.balance_after:.2f}",
                'Notes': tx.notes or ''
            })
        
        df = pd.DataFrame(tx_data)
        file_path = os.path.join(self.output_dir, filename)
        df.to_csv(file_path, index=False)
    
    def generate_customer_analysis_report(self, customer_id: str,
                                        start_date: Optional[datetime] = None,
                                        end_date: Optional[datetime] = None) -> Dict:
        """
        Generate comprehensive customer analysis
        
        Returns:
            Dictionary with analysis data
        """
        if start_date is None:
            # Default to last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        elif end_date is None:
            end_date = datetime.now()
        
        # Get basic statistics
        stats = self.trading_service.calculate_trading_statistics(
            customer_id, start_date, end_date
        )
        
        # Get transactions for pattern analysis
        transactions = self.trading_service.get_customer_transactions(
            customer_id, start_date, end_date
        )
        
        # Analyze trading patterns
        patterns = self._analyze_trading_patterns(transactions)
        
        # Get current positions
        positions = self.trading_service.get_customer_positions(customer_id)
        
        # Calculate risk metrics
        account = self.trading_service.accounts.get(customer_id)
        risk_metrics = self._calculate_risk_metrics(account, positions) if account else {}
        
        return {
            'customer_id': customer_id,
            'analysis_period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'trading_statistics': stats,
            'trading_patterns': patterns,
            'current_positions': len(positions),
            'risk_metrics': risk_metrics
        }
    
    def _analyze_trading_patterns(self, transactions: List) -> Dict:
        """Analyze trading patterns from transactions"""
        if not transactions:
            return {
                'most_traded_instrument': None,
                'trading_frequency': 0,
                'average_trade_size': 0,
                'preferred_trading_hours': []
            }
        
        # Most traded instrument
        instruments = {}
        trade_sizes = []
        trading_hours = []
        
        for tx in transactions:
            instruments[tx.instrument] = instruments.get(tx.instrument, 0) + 1
            trade_sizes.append(tx.quantity)
            trading_hours.append(tx.timestamp.hour)
        
        most_traded = max(instruments.items(), key=lambda x: x[1])[0] if instruments else None
        
        # Trading hours analysis
        hour_counts = {}
        for hour in trading_hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        preferred_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'most_traded_instrument': most_traded,
            'trading_frequency': len(transactions),
            'average_trade_size': sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0,
            'preferred_trading_hours': [f"{h}:00" for h, _ in preferred_hours]
        }
    
    def _calculate_risk_metrics(self, account, positions: List) -> Dict:
        """Calculate risk metrics for account"""
        if not account:
            return {}
        
        total_exposure = sum(
            pos.quantity * pos.entry_price * pos.leverage
            for pos in positions
        )
        
        return {
            'account_balance': account.balance,
            'account_equity': account.equity,
            'margin_used': account.margin_used,
            'margin_available': account.margin_available,
            'margin_level': account.margin_level,
            'total_exposure': total_exposure,
            'unrealized_pnl': account.unrealized_pnl,
            'realized_pnl': account.realized_pnl
        }
