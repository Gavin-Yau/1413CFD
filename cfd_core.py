import pandas as pd
import os
import requests
import math
import datetime
import time

# ==========================================
# ⚙️ 数据库配置 (V3.1 字段增强版)
# ==========================================
DB_FILE = "CFD_System_Pro.xlsx"
SHEET_MAIN = "交易总台账"      
SHEET_CLIENT = "客户订单台账" 

def get_realtime_price(stock_code):
    """API 获取股价"""
    stock_code = str(stock_code).strip().split('.')[0]
    if stock_code.startswith('6'): prefix = "sh"
    elif stock_code.startswith(('0', '3')): prefix = "sz"
    elif stock_code.startswith(('4', '8')): prefix = "bj"
    else: return "未知标的", 0.0

    try:
        url = f"http://hq.sinajs.cn/list={prefix}{stock_code}"
        resp = requests.get(url, headers={'Referer': 'http://finance.sina.com.cn'}, timeout=1.5)
        text = resp.text
        if '="' in text:
            content = text.split('="')[1]
            parts = content.split(',')
            if len(parts) > 3:
                name = parts[0]
                current_price = float(parts[3]) 
                if current_price == 0: current_price = float(parts[2])
                return name, current_price
    except:
        pass
    return "未知标的", 0.0

def init_db():
    if not os.path.exists(DB_FILE):
        # 实盘表
        cols_main = [
            "订单编号", "状态", "下单时间", "平仓时间", 
            "客户", "标的代码", "标的名称",
            "客户目标本金", "指令价格",
            "实际成交均价", "实际股数", "实际持仓本金",
            "风险敞口(Gap)", "保证金(收)", "服务费(收)", 
            "预警线", "平仓线", 
            "平仓/强平价", "最终盈亏", "备注", 
            "关联外部ID" 
        ]
        # 客户指令表 (🆕 增加了预警和止损列)
        cols_client = [
            "指令单号", "接收时间", "原始文本",
            "客户姓名", "标的代码", "标的名称(API)", 
            "买卖方向", "指令价格", "目标本金",
            "解析保证金", "应收保证金(5%)", "保证金核验",
            "解析服务费", "应收服务费(1.3%)", "服务费核验",
            "解析预警价", "解析止损价", # 🔥 新增
            "录入状态"
        ]
        try:
            with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
                pd.DataFrame(columns=cols_main).to_excel(writer, sheet_name=SHEET_MAIN, index=False)
                pd.DataFrame(columns=cols_client).to_excel(writer, sheet_name=SHEET_CLIENT, index=False)
            print(f"✅ 数据库已初始化: {DB_FILE}")
        except PermissionError:
            print("❌ 初始化失败：文件被占用")

def load_db():
    if not os.path.exists(DB_FILE): init_db()
    while True:
        try:
            with pd.ExcelFile(DB_FILE, engine='openpyxl') as xls:
                if SHEET_MAIN in xls.sheet_names:
                    df_main = pd.read_excel(xls, SHEET_MAIN, dtype={'订单编号': str, '标的代码': str})
                else: df_main = pd.DataFrame()
                
                if SHEET_CLIENT in xls.sheet_names:
                    df_client = pd.read_excel(xls, SHEET_CLIENT, dtype={'指令单号': str, '标的代码': str})
                else: df_client = pd.DataFrame()
                return df_main, df_client
        except PermissionError:
            input("🚫 Excel 被占用，请关闭后按回车重试...")
            continue
        except Exception as e:
            print(f"❌ 读取错误: {e}")
            return pd.DataFrame(), pd.DataFrame()

def save_db(df_main, df_client):
    while True:
        try:
            with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='w') as writer:
                df_main.to_excel(writer, sheet_name=SHEET_MAIN, index=False)
                df_client.to_excel(writer, sheet_name=SHEET_CLIENT, index=False)
            return
        except PermissionError:
            import winsound
            winsound.Beep(500, 500)
            input("🚫 写入失败！请关闭 Excel 后按回车保存...")
            continue

def calculate_shares_and_gap(code, target_money, price):
    if price <= 0: return 0, 0, 0
    raw_shares = target_money / price
    if str(code).startswith("688"):
        actual_shares = math.floor(raw_shares)
    else:
        actual_shares = math.floor(raw_shares / 100) * 100
    actual_money = actual_shares * price
    gap = target_money - actual_money
    return actual_shares, actual_money, gap
