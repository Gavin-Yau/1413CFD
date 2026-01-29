"""
Risk Control and Early Warning System
"""
from typing import List, Dict, Optional
from datetime import datetime
from models import Position, Account, Alert, OrderSide
from config import Config
import uuid


class RiskControlService:
    """Risk control and monitoring service"""
    
    def __init__(self):
        self.max_position_size = Config.MAX_POSITION_SIZE
        self.max_leverage = Config.MAX_LEVERAGE
        self.margin_call_threshold = Config.MARGIN_CALL_THRESHOLD
        self.stop_out_level = Config.STOP_OUT_LEVEL
        self.profit_alert_threshold = Config.PROFIT_ALERT_THRESHOLD
        self.loss_alert_threshold = Config.LOSS_ALERT_THRESHOLD
        
    def check_position_risk(self, position: Position) -> List[Alert]:
        """
        Check risk for a single position
        
        Returns:
            List of alerts if any risk detected
        """
        alerts = []
        
        # Check leverage
        if position.leverage > self.max_leverage:
            alerts.append(self._create_alert(
                customer_id=position.customer_id,
                alert_type="high_leverage",
                severity="warning",
                title="高杠杆警告 (High Leverage Warning)",
                message=f"持仓 {position.instrument} 杠杆为 {position.leverage}x，超过最大限制 {self.max_leverage}x",
                data={"position_id": position.position_id, "leverage": position.leverage}
            ))
        
        # Check unrealized P&L
        if position.unrealized_pnl < self.loss_alert_threshold:
            alerts.append(self._create_alert(
                customer_id=position.customer_id,
                alert_type="large_loss",
                severity="critical",
                title="重大亏损警告 (Large Loss Alert)",
                message=f"持仓 {position.instrument} 浮亏 {position.unrealized_pnl:.2f}，超过警戒线",
                data={"position_id": position.position_id, "unrealized_pnl": position.unrealized_pnl}
            ))
        
        if position.unrealized_pnl > self.profit_alert_threshold:
            alerts.append(self._create_alert(
                customer_id=position.customer_id,
                alert_type="large_profit",
                severity="info",
                title="盈利提醒 (Profit Alert)",
                message=f"持仓 {position.instrument} 浮盈 {position.unrealized_pnl:.2f}，建议考虑止盈",
                data={"position_id": position.position_id, "unrealized_pnl": position.unrealized_pnl}
            ))
        
        return alerts
    
    def check_account_risk(self, account: Account, positions: List[Position]) -> List[Alert]:
        """
        Check overall account risk
        
        Returns:
            List of alerts if any risk detected
        """
        alerts = []
        
        # Calculate margin level
        if account.margin_used > 0:
            margin_level = account.equity / account.margin_used
        else:
            margin_level = float('inf')
        
        # Margin call check
        if margin_level < self.margin_call_threshold:
            alerts.append(self._create_alert(
                customer_id=account.customer_id,
                alert_type="margin_call",
                severity="critical",
                title="保证金追加通知 (Margin Call)",
                message=f"账户保证金水平 {margin_level*100:.2f}%，低于 {self.margin_call_threshold*100:.2f}%，请补充保证金",
                data={"margin_level": margin_level, "equity": account.equity, "margin_used": account.margin_used}
            ))
        
        # Stop out level check
        if margin_level < self.stop_out_level:
            alerts.append(self._create_alert(
                customer_id=account.customer_id,
                alert_type="stop_out",
                severity="critical",
                title="强制平仓警告 (Stop Out Warning)",
                message=f"账户保证金水平 {margin_level*100:.2f}%，达到强制平仓线 {self.stop_out_level*100:.2f}%",
                data={"margin_level": margin_level, "equity": account.equity, "margin_used": account.margin_used}
            ))
        
        # Check total exposure
        total_exposure = sum(pos.quantity * pos.entry_price * pos.leverage for pos in positions)
        if total_exposure > self.max_position_size * len(positions):
            alerts.append(self._create_alert(
                customer_id=account.customer_id,
                alert_type="excessive_exposure",
                severity="warning",
                title="持仓过度警告 (Excessive Exposure)",
                message=f"总持仓风险敞口 {total_exposure:.2f} 过大",
                data={"total_exposure": total_exposure}
            ))
        
        # Check account drawdown
        if account.balance > 0:
            drawdown = (account.balance - account.equity) / account.balance
            if drawdown > 0.2:  # 20% drawdown
                alerts.append(self._create_alert(
                    customer_id=account.customer_id,
                    alert_type="high_drawdown",
                    severity="warning",
                    title="回撤警告 (Drawdown Alert)",
                    message=f"账户回撤达到 {drawdown*100:.2f}%，建议控制风险",
                    data={"drawdown": drawdown}
                ))
        
        return alerts
    
    def calculate_position_pnl(self, position: Position, current_price: float) -> float:
        """
        Calculate unrealized P&L for a position
        
        Args:
            position: Position object
            current_price: Current market price
            
        Returns:
            Unrealized P&L
        """
        if position.side == OrderSide.BUY:
            # Long position
            pnl = (current_price - position.entry_price) * position.quantity
        else:
            # Short position
            pnl = (position.entry_price - current_price) * position.quantity
        
        return pnl
    
    def update_position_pnl(self, position: Position, current_price: float) -> Position:
        """
        Update position with current P&L
        
        Args:
            position: Position object
            current_price: Current market price
            
        Returns:
            Updated position
        """
        position.current_price = current_price
        position.unrealized_pnl = self.calculate_position_pnl(position, current_price)
        position.updated_at = datetime.now()
        return position
    
    def calculate_required_margin(self, instrument: str, quantity: float, 
                                  price: float, leverage: float) -> float:
        """
        Calculate required margin for a position
        
        Args:
            instrument: Trading instrument
            quantity: Position quantity
            price: Entry price
            leverage: Leverage ratio
            
        Returns:
            Required margin
        """
        position_value = quantity * price
        required_margin = position_value / leverage
        return required_margin
    
    def can_open_position(self, account: Account, instrument: str, 
                         quantity: float, price: float, leverage: float) -> tuple[bool, str]:
        """
        Check if account can open a new position
        
        Returns:
            Tuple of (can_open, reason)
        """
        required_margin = self.calculate_required_margin(instrument, quantity, price, leverage)
        
        if required_margin > account.margin_available:
            return False, f"保证金不足 (Insufficient margin): 需要 {required_margin:.2f}, 可用 {account.margin_available:.2f}"
        
        if leverage > self.max_leverage:
            return False, f"杠杆过高 (Leverage too high): {leverage}x > {self.max_leverage}x"
        
        position_value = quantity * price
        if position_value > self.max_position_size:
            return False, f"持仓规模过大 (Position too large): {position_value:.2f} > {self.max_position_size:.2f}"
        
        return True, ""
    
    def _create_alert(self, customer_id: str, alert_type: str, severity: str,
                     title: str, message: str, data: Optional[Dict] = None) -> Alert:
        """Create an alert object"""
        return Alert(
            alert_id=str(uuid.uuid4()),
            customer_id=customer_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            triggered_at=datetime.now(),
            acknowledged=False,
            data=data
        )
    
    def get_position_risk_score(self, position: Position) -> float:
        """
        Calculate risk score for a position (0-100)
        Higher score means higher risk
        
        Returns:
            Risk score
        """
        score = 0.0
        
        # Leverage factor (0-40 points)
        leverage_score = min((position.leverage / self.max_leverage) * 40, 40)
        score += leverage_score
        
        # Loss factor (0-40 points)
        if position.unrealized_pnl < 0:
            loss_ratio = abs(position.unrealized_pnl) / (position.quantity * position.entry_price)
            loss_score = min(loss_ratio * 200, 40)  # 20% loss = 40 points
            score += loss_score
        
        # Position size factor (0-20 points)
        position_value = position.quantity * position.entry_price * position.leverage
        size_score = min((position_value / self.max_position_size) * 20, 20)
        score += size_score
        
        return min(score, 100.0)
    
    def get_account_risk_score(self, account: Account) -> float:
        """
        Calculate risk score for an account (0-100)
        Higher score means higher risk
        
        Returns:
            Risk score
        """
        score = 0.0
        
        # Margin level factor (0-50 points)
        if account.margin_used > 0:
            margin_level = account.equity / account.margin_used
            if margin_level < 1.0:
                score += 50
            elif margin_level < 2.0:
                score += 30
            elif margin_level < 3.0:
                score += 10
        
        # Drawdown factor (0-30 points)
        if account.balance > 0:
            drawdown = (account.balance - account.equity) / account.balance
            drawdown_score = min(drawdown * 150, 30)  # 20% drawdown = 30 points
            score += drawdown_score
        
        # Losing trades ratio (0-20 points)
        if account.total_trades > 0:
            loss_ratio = account.losing_trades / account.total_trades
            score += loss_ratio * 20
        
        return min(score, 100.0)
