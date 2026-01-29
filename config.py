"""
Configuration settings for CFD Backend System
"""
import os
from typing import Dict, Any

class Config:
    """Base configuration"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///cfd_system.db')
    
    # Risk Control Settings
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '100000'))
    MAX_LEVERAGE = float(os.getenv('MAX_LEVERAGE', '10'))
    MARGIN_CALL_THRESHOLD = float(os.getenv('MARGIN_CALL_THRESHOLD', '0.3'))
    STOP_OUT_LEVEL = float(os.getenv('STOP_OUT_LEVEL', '0.2'))
    
    # Alert Thresholds
    PROFIT_ALERT_THRESHOLD = float(os.getenv('PROFIT_ALERT_THRESHOLD', '1000'))
    LOSS_ALERT_THRESHOLD = float(os.getenv('LOSS_ALERT_THRESHOLD', '-500'))
    
    # Report Settings
    REPORT_OUTPUT_DIR = os.getenv('REPORT_OUTPUT_DIR', './reports')
    DAILY_REPORT_TIME = os.getenv('DAILY_REPORT_TIME', '23:00')
    WEEKLY_REPORT_DAY = os.getenv('WEEKLY_REPORT_DAY', 'Sunday')
    MONTHLY_REPORT_DAY = int(os.getenv('MONTHLY_REPORT_DAY', '1'))
    
    # NLP Settings
    NLP_MODEL = os.getenv('NLP_MODEL', 'jieba')
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))
    
    # Notification Settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
    
    # Timezone
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }
