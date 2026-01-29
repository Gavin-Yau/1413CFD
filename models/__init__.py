"""
Core data models for CFD Trading System
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    CLOSED = "closed"


class InstrumentType(str, Enum):
    """CFD Instrument types"""
    FOREX = "forex"
    STOCK = "stock"
    COMMODITY = "commodity"
    INDEX = "index"
    CRYPTO = "crypto"


class Order(BaseModel):
    """CFD Order model"""
    order_id: str = Field(..., description="Unique order identifier")
    customer_id: str = Field(..., description="Customer identifier")
    instrument: str = Field(..., description="Trading instrument symbol")
    instrument_type: InstrumentType = Field(..., description="Type of instrument")
    order_type: OrderType = Field(..., description="Type of order")
    side: OrderSide = Field(..., description="Buy or Sell")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Order price (for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price")
    status: OrderStatus = Field(OrderStatus.PENDING, description="Order status")
    leverage: float = Field(1.0, ge=1, le=100, description="Leverage ratio")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    filled_quantity: float = Field(0.0, ge=0, description="Filled quantity")
    average_fill_price: Optional[float] = Field(None, description="Average fill price")
    commission: float = Field(0.0, ge=0, description="Commission charged")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        use_enum_values = True


class Position(BaseModel):
    """Trading position model"""
    position_id: str = Field(..., description="Unique position identifier")
    customer_id: str = Field(..., description="Customer identifier")
    instrument: str = Field(..., description="Trading instrument symbol")
    instrument_type: InstrumentType = Field(..., description="Type of instrument")
    side: OrderSide = Field(..., description="Long or Short position")
    quantity: float = Field(..., gt=0, description="Position quantity")
    entry_price: float = Field(..., gt=0, description="Average entry price")
    current_price: Optional[float] = Field(None, description="Current market price")
    leverage: float = Field(1.0, ge=1, description="Leverage used")
    margin_used: float = Field(..., gt=0, description="Margin used for position")
    unrealized_pnl: float = Field(0.0, description="Unrealized profit/loss")
    realized_pnl: float = Field(0.0, description="Realized profit/loss")
    opened_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class Transaction(BaseModel):
    """Transaction record model"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    customer_id: str = Field(..., description="Customer identifier")
    order_id: str = Field(..., description="Related order ID")
    position_id: Optional[str] = Field(None, description="Related position ID")
    instrument: str = Field(..., description="Trading instrument")
    transaction_type: str = Field(..., description="Transaction type")
    quantity: float = Field(..., description="Transaction quantity")
    price: float = Field(..., description="Transaction price")
    amount: float = Field(..., description="Transaction amount")
    commission: float = Field(0.0, description="Commission fee")
    pnl: float = Field(0.0, description="Profit/Loss")
    balance_after: float = Field(..., description="Account balance after transaction")
    timestamp: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = Field(None, description="Transaction notes")


class Account(BaseModel):
    """Customer account model"""
    account_id: str = Field(..., description="Unique account identifier")
    customer_id: str = Field(..., description="Customer identifier")
    customer_name: str = Field(..., description="Customer name")
    balance: float = Field(..., ge=0, description="Account balance")
    equity: float = Field(..., ge=0, description="Account equity")
    margin_used: float = Field(0.0, ge=0, description="Total margin used")
    margin_available: float = Field(..., ge=0, description="Available margin")
    margin_level: float = Field(100.0, description="Margin level percentage")
    unrealized_pnl: float = Field(0.0, description="Total unrealized P&L")
    realized_pnl: float = Field(0.0, description="Total realized P&L")
    total_trades: int = Field(0, ge=0, description="Total number of trades")
    winning_trades: int = Field(0, ge=0, description="Number of winning trades")
    losing_trades: int = Field(0, ge=0, description="Number of losing trades")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: str = Field("active", description="Account status")


class Alert(BaseModel):
    """Alert/Notification model"""
    alert_id: str = Field(..., description="Unique alert identifier")
    customer_id: str = Field(..., description="Customer identifier")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity (info, warning, critical)")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    triggered_at: datetime = Field(default_factory=datetime.now)
    acknowledged: bool = Field(False, description="Whether alert was acknowledged")
    data: Optional[dict] = Field(None, description="Additional alert data")


class Report(BaseModel):
    """Report model"""
    report_id: str = Field(..., description="Unique report identifier")
    report_type: str = Field(..., description="Type of report (daily/weekly/monthly)")
    customer_id: Optional[str] = Field(None, description="Customer ID (None for system-wide)")
    start_date: datetime = Field(..., description="Report period start")
    end_date: datetime = Field(..., description="Report period end")
    total_trades: int = Field(0, description="Total number of trades")
    total_pnl: float = Field(0.0, description="Total profit/loss")
    winning_trades: int = Field(0, description="Number of winning trades")
    losing_trades: int = Field(0, description="Number of losing trades")
    total_commission: float = Field(0.0, description="Total commission paid")
    largest_win: float = Field(0.0, description="Largest winning trade")
    largest_loss: float = Field(0.0, description="Largest losing trade")
    average_win: float = Field(0.0, description="Average winning trade")
    average_loss: float = Field(0.0, description="Average losing trade")
    win_rate: float = Field(0.0, description="Win rate percentage")
    profit_factor: float = Field(0.0, description="Profit factor")
    generated_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = Field(None, description="Path to generated report file")
    data: Optional[dict] = Field(None, description="Additional report data")
