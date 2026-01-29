"""
Natural Language Processing service for parsing trading orders
Supports Chinese and English order instructions
"""
import re
from typing import Dict, Optional, Tuple
import jieba
from models import Order, OrderType, OrderSide, InstrumentType, OrderStatus
from datetime import datetime
import uuid


class OrderNLPParser:
    """Parse natural language trading instructions"""
    
    def __init__(self):
        """Initialize NLP parser with trading vocabulary"""
        # Add custom trading terms to jieba dictionary
        trading_terms = [
            '买入', '卖出', '做多', '做空', '开仓', '平仓',
            '市价', '限价', '止损', '止盈', '杠杆',
            '外汇', '股票', '商品', '指数', '加密货币'
        ]
        for term in trading_terms:
            jieba.add_word(term)
        
        # Action keywords mapping
        self.action_keywords = {
            'buy': ['买入', '买', '做多', 'buy', 'long', '开多'],
            'sell': ['卖出', '卖', '做空', 'sell', 'short', '开空']
        }
        
        # Order type keywords
        self.order_type_keywords = {
            'market': ['市价', 'market', '市价单'],
            'limit': ['限价', 'limit', '限价单'],
            'stop': ['止损', 'stop', '止损单'],
            'stop_limit': ['止损限价', 'stop_limit']
        }
        
        # Instrument type keywords
        self.instrument_type_keywords = {
            'forex': ['外汇', 'forex', 'fx', '货币对'],
            'stock': ['股票', 'stock', '股'],
            'commodity': ['商品', 'commodity', '大宗商品'],
            'index': ['指数', 'index'],
            'crypto': ['加密货币', 'crypto', '数字货币', '比特币', '以太坊']
        }
    
    def parse_order_instruction(self, instruction: str, customer_id: str) -> Optional[Dict]:
        """
        Parse natural language order instruction
        
        Args:
            instruction: Natural language order instruction
            customer_id: Customer ID
            
        Returns:
            Dictionary with parsed order parameters or None if parsing fails
        """
        instruction = instruction.lower().strip()
        
        # Parse order side (buy/sell)
        side = self._parse_side(instruction)
        if not side:
            return None
        
        # Parse instrument
        instrument = self._parse_instrument(instruction)
        if not instrument:
            return None
        
        # Parse instrument type
        instrument_type = self._parse_instrument_type(instruction)
        
        # Parse quantity
        quantity = self._parse_quantity(instruction)
        if not quantity:
            return None
        
        # Parse order type
        order_type = self._parse_order_type(instruction)
        
        # Parse price (for limit orders)
        price = self._parse_price(instruction)
        
        # Parse leverage
        leverage = self._parse_leverage(instruction)
        
        # Generate order
        order_data = {
            'order_id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'instrument': instrument,
            'instrument_type': instrument_type,
            'order_type': order_type,
            'side': side,
            'quantity': quantity,
            'price': price,
            'leverage': leverage,
            'status': OrderStatus.PENDING,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'filled_quantity': 0.0,
            'commission': 0.0
        }
        
        return order_data
    
    def _parse_side(self, instruction: str) -> Optional[OrderSide]:
        """Parse order side from instruction"""
        for side, keywords in self.action_keywords.items():
            for keyword in keywords:
                if keyword in instruction:
                    return OrderSide.BUY if side == 'buy' else OrderSide.SELL
        return None
    
    def _parse_order_type(self, instruction: str) -> OrderType:
        """Parse order type from instruction"""
        for order_type, keywords in self.order_type_keywords.items():
            for keyword in keywords:
                if keyword in instruction:
                    if order_type == 'market':
                        return OrderType.MARKET
                    elif order_type == 'limit':
                        return OrderType.LIMIT
                    elif order_type == 'stop':
                        return OrderType.STOP
                    elif order_type == 'stop_limit':
                        return OrderType.STOP_LIMIT
        # Default to market order
        return OrderType.MARKET
    
    def _parse_instrument_type(self, instruction: str) -> InstrumentType:
        """Parse instrument type from instruction"""
        for inst_type, keywords in self.instrument_type_keywords.items():
            for keyword in keywords:
                if keyword in instruction:
                    if inst_type == 'forex':
                        return InstrumentType.FOREX
                    elif inst_type == 'stock':
                        return InstrumentType.STOCK
                    elif inst_type == 'commodity':
                        return InstrumentType.COMMODITY
                    elif inst_type == 'index':
                        return InstrumentType.INDEX
                    elif inst_type == 'crypto':
                        return InstrumentType.CRYPTO
        # Default to forex
        return InstrumentType.FOREX
    
    def _parse_instrument(self, instruction: str) -> Optional[str]:
        """Parse instrument symbol from instruction"""
        # First check for commodity names (Chinese and English)
        commodity_map = {
            '黄金': 'GOLD',
            '白银': 'SILVER',
            '原油': 'OIL',
            '天然气': 'GAS',
            'gold': 'GOLD',
            'silver': 'SILVER',
            'oil': 'OIL',
            'gas': 'GAS'
        }
        
        for name, symbol in commodity_map.items():
            if name in instruction.lower():
                return symbol
        
        # Then check for forex and stock symbols
        patterns = [
            r'\b([A-Z]{6})\b',  # Forex pairs like EURUSD
            r'([A-Z]{3}/[A-Z]{3})',  # Forex pairs like EUR/USD
            r'\b([A-Z]{2,5})\b',  # Stock symbols (word boundary to avoid matching within words)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction)
            if match:
                symbol = match.group(1).upper()
                # Clean up symbol
                symbol = symbol.replace('/', '')
                # Skip common words that shouldn't be instruments
                if symbol not in ['AT', 'LOT', 'LEVERAGE', 'LEVERA', 'BUY', 'SELL']:
                    return symbol
        
        return None
    
    def _parse_quantity(self, instruction: str) -> Optional[float]:
        """Parse quantity from instruction"""
        # Patterns for quantity
        patterns = [
            r'(\d+\.?\d*)\s*手',  # Chinese: X 手
            r'(\d+\.?\d*)\s*lot',  # English: X lots
            r'(\d+\.?\d*)\s*股',  # Chinese: X 股
            r'(\d+\.?\d*)\s*shares',  # English: X shares
            r'数量[:：]?\s*(\d+\.?\d*)',  # Chinese: 数量: X
            r'quantity[:：]?\s*(\d+\.?\d*)',  # English: quantity: X
            r'(\d+\.?\d*)\s*单位',  # Chinese: X 单位
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        # Try to find any number as fallback
        match = re.search(r'(\d+\.?\d*)', instruction)
        if match:
            return float(match.group(1))
        
        return None
    
    def _parse_price(self, instruction: str) -> Optional[float]:
        """Parse price from instruction (for limit orders)"""
        patterns = [
            r'价格[:：]?\s*(\d+\.?\d*)',  # Chinese: 价格: X
            r'price[:：]?\s*(\d+\.?\d*)',  # English: price: X
            r'@\s*(\d+\.?\d*)',  # @ X format
            r'在\s*(\d+\.?\d*)',  # Chinese: 在 X
            r'at\s*(\d+\.?\d*)',  # English: at X
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _parse_leverage(self, instruction: str) -> float:
        """Parse leverage from instruction"""
        patterns = [
            r'杠杆[:：]?\s*(\d+)',  # Chinese: 杠杆: X
            r'leverage[:：]?\s*(\d+)',  # English: leverage: X
            r'(\d+)\s*倍',  # Chinese: X 倍
            r'(\d+)x',  # X times
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                leverage = int(match.group(1))
                # Limit leverage to reasonable range
                return min(max(leverage, 1), 100)
        
        # Default leverage
        return 1.0
    
    def validate_order(self, order_data: Dict) -> Tuple[bool, str]:
        """
        Validate parsed order data
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not order_data.get('instrument'):
            return False, "无法识别交易品种 (Cannot identify instrument)"
        
        if not order_data.get('quantity') or order_data['quantity'] <= 0:
            return False, "无效的交易数量 (Invalid quantity)"
        
        if order_data.get('order_type') == OrderType.LIMIT and not order_data.get('price'):
            return False, "限价单需要指定价格 (Limit order requires price)"
        
        if order_data.get('leverage', 1) > 100:
            return False, "杠杆倍数过高 (Leverage too high)"
        
        return True, ""
    
    def generate_confirmation_message(self, order_data: Dict) -> str:
        """Generate human-readable order confirmation message"""
        side_text = "买入" if order_data['side'] == OrderSide.BUY else "卖出"
        order_type_text = {
            OrderType.MARKET: "市价单",
            OrderType.LIMIT: "限价单",
            OrderType.STOP: "止损单",
            OrderType.STOP_LIMIT: "止损限价单"
        }.get(order_data['order_type'], "市价单")
        
        msg = f"订单确认:\n"
        msg += f"类型: {order_type_text}\n"
        msg += f"操作: {side_text}\n"
        msg += f"品种: {order_data['instrument']}\n"
        msg += f"数量: {order_data['quantity']}\n"
        
        if order_data.get('price'):
            msg += f"价格: {order_data['price']}\n"
        
        if order_data.get('leverage', 1) > 1:
            msg += f"杠杆: {order_data['leverage']}x\n"
        
        msg += f"订单ID: {order_data['order_id']}"
        
        return msg
