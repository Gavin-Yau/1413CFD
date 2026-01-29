"""
Notification Service for alerts and reports
Supports multiple channels: console, file, telegram, SMS
"""
from typing import List, Optional
from datetime import datetime
import os
from models import Alert, Report
from config import Config


class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self):
        self.telegram_enabled = bool(Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID)
        self.sms_enabled = bool(Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN)
        
        # Create logs directory for file notifications
        self.log_dir = "./logs"
        os.makedirs(self.log_dir, exist_ok=True)
    
    def send_alert(self, alert: Alert, channels: Optional[List[str]] = None):
        """
        Send alert through specified channels
        
        Args:
            alert: Alert object
            channels: List of channels (console, file, telegram, sms)
                     If None, uses default channels based on severity
        """
        if channels is None:
            # Default channels based on severity
            if alert.severity == "critical":
                channels = ["console", "file", "telegram", "sms"]
            elif alert.severity == "warning":
                channels = ["console", "file", "telegram"]
            else:
                channels = ["console", "file"]
        
        for channel in channels:
            if channel == "console":
                self._send_console_alert(alert)
            elif channel == "file":
                self._send_file_alert(alert)
            elif channel == "telegram" and self.telegram_enabled:
                self._send_telegram_alert(alert)
            elif channel == "sms" and self.sms_enabled:
                self._send_sms_alert(alert)
    
    def send_report_notification(self, report: Report, recipients: Optional[List[str]] = None):
        """
        Send report notification
        
        Args:
            report: Report object
            recipients: List of recipient identifiers (customer IDs or phone numbers)
        """
        message = self._format_report_notification(report)
        
        # Console notification
        print(f"\n{'='*60}")
        print("REPORT GENERATED")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        
        # File notification
        self._log_to_file(f"REPORT: {message}")
        
        # Optional: Send via telegram/sms if recipients specified
        if recipients and self.telegram_enabled:
            self._send_telegram_message(message)
    
    def _send_console_alert(self, alert: Alert):
        """Send alert to console"""
        severity_colors = {
            "info": "INFO",
            "warning": "WARNING",
            "critical": "CRITICAL"
        }
        
        print(f"\n[{severity_colors.get(alert.severity, 'ALERT')}] {alert.title}")
        print(f"Customer: {alert.customer_id}")
        print(f"Time: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Message: {alert.message}")
        if alert.data:
            print(f"Data: {alert.data}")
        print()
    
    def _send_file_alert(self, alert: Alert):
        """Log alert to file"""
        log_message = (
            f"[{alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"[{alert.severity.upper()}] "
            f"[{alert.alert_type}] "
            f"Customer: {alert.customer_id} - "
            f"{alert.title}: {alert.message}"
        )
        
        if alert.data:
            log_message += f" | Data: {alert.data}"
        
        self._log_to_file(log_message)
    
    def _send_telegram_alert(self, alert: Alert):
        """Send alert via Telegram"""
        try:
            # Placeholder for Telegram integration
            # In production, would use python-telegram-bot library
            message = f"🚨 *{alert.title}*\n\n"
            message += f"客户: {alert.customer_id}\n"
            message += f"严重程度: {alert.severity}\n"
            message += f"消息: {alert.message}\n"
            message += f"时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Log that telegram would be sent
            self._log_to_file(f"TELEGRAM: {message}")
            print(f"[Telegram notification would be sent]: {alert.title}")
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")
    
    def _send_sms_alert(self, alert: Alert):
        """Send alert via SMS"""
        try:
            # Placeholder for Twilio SMS integration
            # In production, would use Twilio client
            message = f"{alert.title}: {alert.message}"
            
            # Log that SMS would be sent
            self._log_to_file(f"SMS: {message}")
            print(f"[SMS notification would be sent]: {alert.title}")
        except Exception as e:
            print(f"Failed to send SMS alert: {e}")
    
    def _send_telegram_message(self, message: str):
        """Send generic message via Telegram"""
        try:
            # Placeholder for Telegram integration
            self._log_to_file(f"TELEGRAM: {message}")
            print(f"[Telegram message would be sent]")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
    
    def _log_to_file(self, message: str):
        """Log message to file"""
        log_file = os.path.join(
            self.log_dir,
            f"notifications_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    
    def _format_report_notification(self, report: Report) -> str:
        """Format report notification message"""
        message = f"交易报告已生成 (Trading Report Generated)\n\n"
        message += f"报告类型 (Type): {report.report_type}\n"
        message += f"周期 (Period): {report.start_date.strftime('%Y-%m-%d')} 到 {report.end_date.strftime('%Y-%m-%d')}\n"
        
        if report.customer_id:
            message += f"客户 (Customer): {report.customer_id}\n"
        else:
            message += f"范围 (Scope): 系统全局 (System-wide)\n"
        
        message += f"\n交易统计 (Trading Statistics):\n"
        message += f"- 总交易数 (Total Trades): {report.total_trades}\n"
        message += f"- 盈利交易 (Winning): {report.winning_trades}\n"
        message += f"- 亏损交易 (Losing): {report.losing_trades}\n"
        message += f"- 胜率 (Win Rate): {report.win_rate:.2f}%\n"
        message += f"- 总盈亏 (Total P&L): {report.total_pnl:.2f}\n"
        message += f"- 最大盈利 (Largest Win): {report.largest_win:.2f}\n"
        message += f"- 最大亏损 (Largest Loss): {report.largest_loss:.2f}\n"
        message += f"- 盈亏比 (Profit Factor): {report.profit_factor:.2f}\n"
        
        if report.file_path:
            message += f"\n报告文件 (Report File): {report.file_path}\n"
        
        return message
    
    def send_daily_summary(self, summary_data: dict):
        """Send daily summary notification"""
        message = "每日交易总结 (Daily Trading Summary)\n\n"
        message += f"日期 (Date): {datetime.now().strftime('%Y-%m-%d')}\n"
        message += f"总交易数 (Total Trades): {summary_data.get('total_trades', 0)}\n"
        message += f"总盈亏 (Total P&L): {summary_data.get('total_pnl', 0):.2f}\n"
        message += f"活跃客户 (Active Customers): {summary_data.get('active_customers', 0)}\n"
        
        print(f"\n{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        
        self._log_to_file(f"DAILY SUMMARY: {message}")
    
    def send_margin_call_notification(self, customer_id: str, margin_level: float):
        """Send margin call notification"""
        alert = Alert(
            alert_id=f"MC_{customer_id}_{datetime.now().timestamp()}",
            customer_id=customer_id,
            alert_type="margin_call",
            severity="critical",
            title="保证金追加通知 (Margin Call)",
            message=f"账户保证金水平 {margin_level*100:.2f}%，请立即补充保证金！",
            triggered_at=datetime.now(),
            acknowledged=False,
            data={"margin_level": margin_level}
        )
        
        self.send_alert(alert, channels=["console", "file", "telegram", "sms"])
    
    def send_position_closed_notification(self, customer_id: str, instrument: str, 
                                        pnl: float):
        """Send position closed notification"""
        severity = "info" if pnl >= 0 else "warning"
        title = "持仓已平仓 (Position Closed)"
        message = f"品种 {instrument} 已平仓，盈亏: {pnl:.2f}"
        
        alert = Alert(
            alert_id=f"PC_{customer_id}_{datetime.now().timestamp()}",
            customer_id=customer_id,
            alert_type="position_closed",
            severity=severity,
            title=title,
            message=message,
            triggered_at=datetime.now(),
            acknowledged=False,
            data={"instrument": instrument, "pnl": pnl}
        )
        
        self.send_alert(alert)
