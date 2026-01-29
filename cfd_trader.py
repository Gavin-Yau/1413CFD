import pandas as pd
import datetime
import cfd_core as core
import cfd_smart_parser as parser
import sys
import re

# ==========================================
# 1. 基础开仓 (手动 - 紧急补单用)
# ==========================================
def create_order(is_history=False):
    """手动直接开仓 (写入实盘总账)"""
    print(f"\n📝 {'[历史补录模式]' if is_history else '[实时开仓模式]'}")
    print("⚠️ 注意：此功能直接写入【交易总台账】。日常指令录入请使用 [7. 智能导入]。")
    
    raw_text = input("请粘贴简易指令 (包含代码、金额、客户): ")
    
    code_match = re.search(r'\d{6}', raw_text)
    amt_match = re.search(r'(?:金额|本金|合約金額)[：:\s]*([0-9,]+\.?\d*)', raw_text)
    client_match = re.search(r'(?:客户|客戶)[：:\s]*([^\n\s]+)', raw_text)
    
    if not (code_match and amt_match):
        print("❌ 格式错误：必须包含股票代码和金额")
        return

    code = code_match.group()
    target_notional = float(amt_match.group(1).replace(',', ''))
    client = client_match.group(1) if client_match else "匿名"
    
    if is_history:
        try:
            price = float(input("请输入当时成交价: "))
            time_str = input("请输入下单时间 (YYYY-MM-DD HH:MM:SS): ")
            datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            print("❌ 输入格式错误"); return
    else:
        name, price = core.get_realtime_price(code)
        if price == 0: 
            price = float(input("⚠️ 无法获取市价，请手动输入成交价: "))
        else:
            print(f"📡 实时市价: {price}")
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    name, _ = core.get_realtime_price(code)
    shares, actual_money, gap = core.calculate_shares_and_gap(code, target_notional, price)
    fee = target_notional * (0.011 if target_notional >= 1000000 else 0.013)
    margin = (actual_money * 0.05 // 5000 + 1) * 5000

    df_main, df_client = core.load_db()
    
    day_prefix = time_str.split(' ')[0].replace("-","")
    today_count = len(df_main[df_main['订单编号'].astype(str).str.contains(day_prefix, na=False)])
    order_id = f"{day_prefix}{today_count + 1:04d}"

    new_row = {
        "订单编号": order_id, "状态": "OPEN", 
        "下单时间": time_str, "平仓时间": "-",
        "客户": client, "标的代码": code, "标的名称": name,
        "客户目标本金": target_notional, "指令价格": price,
        "实际成交均价": price, "实际股数": shares, "实际持仓本金": actual_money,
        "风险敞口(Gap)": gap, "保证金(收)": margin, "服务费(收)": fee,
        "预警线": round(price * 0.975, 2), "平仓线": round(price * 0.95, 2),
        "平仓/强平价": "-", "最终盈亏": 0, "备注": "补录" if is_history else "新单",
        "关联外部ID": ""
    }

    df_main = pd.concat([df_main, pd.DataFrame([new_row])], ignore_index=True)
    core.save_db(df_main, df_client)
    
    print(f"\n✅ 开单成功 {order_id}")

# ==========================================
# 2. 订单修正 (修实盘账)
# ==========================================
def update_order():
    df_main, df_client = core.load_db()
    oid = input("请输入要更正的实盘订单号: ")
    if oid not in df_main['订单编号'].values: return print("❌ 找不到订单")
    
    idx = df_main[df_main['订单编号'] == oid].index[0]
    print(f"当前成交价: {df_main.at[idx, '实际成交均价']}")
    
    try:
        new_price = float(input("请输入修正后的成交价: "))
        df_main.at[idx, '实际成交均价'] = new_price
        
        shares = df_main.at[idx, '实际股数']
        df_main.at[idx, '实际持仓本金'] = shares * new_price
        df_main.at[idx, '风险敞口(Gap)'] = df_main.at[idx, '客户目标本金'] - (shares * new_price)
        df_main.at[idx, '预警线'] = round(new_price * 0.975, 2)
        df_main.at[idx, '平仓线'] = round(new_price * 0.95, 2)
        df_main.at[idx, '备注'] = str(df_main.at[idx, '备注']) + "(已修)"
        
        core.save_db(df_main, df_client)
        print("✅ 订单数据已修正")
    except:
        print("❌ 输入无效")

# ==========================================
# 3. 平仓/强平 (操作实盘账)
# ==========================================
def close_position(is_forced=False):
    df_main, df_client = core.load_db()
    opens = df_main[df_main['状态'] == 'OPEN']
    if opens.empty: return print("⚠️ 无持仓订单")
    
    print("-" * 70)
    print(f"{'单号':<15} | {'客户':<6} | {'标的':<8} | {'股数':<6} | {'现价'}")
    print("-" * 70)
    for i, r in opens.iterrows():
        print(f"{r['订单编号']:<15} | {r['客户']:<6} | {r['标的名称']:<8} | {r['实际股数']:<6} | {r['实际成交均价']}")
    print("-" * 70)
    
    oid = input(f"请输入要{'🔴强平' if is_forced else '🔵平仓'}的单号: ").strip()
    if oid not in df_main['订单编号'].values: return print("❌ 单号不存在")
    
    idx = df_main[df_main['订单编号'] == oid].index[0]
    
    code = df_main.at[idx, '标的代码']
    _, mkt_price = core.get_realtime_price(code)
    
    print(f"当前市价: {mkt_price}")
    try:
        in_price = input("确认执行价格 (回车默认市价): ")
        final_price = float(in_price) if in_price else mkt_price
    except:
        print("❌ 价格输入错误"); return
    
    open_price = df_main.at[idx, '实际成交均价']
    shares = df_main.at[idx, '实际股数']
    pnl = (final_price - open_price) * shares
    
    df_main.at[idx, '状态'] = 'LIQUIDATED' if is_forced else 'CLOSED'
    df_main.at[idx, '平仓时间'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_main.at[idx, '平仓/强平价'] = final_price
    df_main.at[idx, '最终盈亏'] = pnl
    
    core.save_db(df_main, df_client)
    print(f"\n✅ 订单已{'强平' if is_forced else '平仓'}结算")
    print(f"   最终盈亏: {pnl:,.2f} 元")

# ==========================================
# 4. 每日结单
# ==========================================
def daily_report():
    df_main, _ = core.load_db()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    df_main['下单时间'] = df_main['下单时间'].fillna('')
    df_main['平仓时间'] = df_main['平仓时间'].fillna('')
    
    daily = df_main[df_main['下单时间'].str.contains(today) | df_main['平仓时间'].str.contains(today)]
    
    print(f"\n📊 === {today} 每日结单 ===")
    print(f"交易总笔数: {len(daily)}")
    print(f"今日总盈亏(已平仓): {daily['最终盈亏'].sum():,.2f}")
    print(f"今日服务费收入: {daily['服务费(收)'].sum():,.2f}")
    
    opens = df_main[df_main['状态'] == 'OPEN']
    total_gap = opens['风险敞口(Gap)'].sum()
    
    print(f"\n⚠️ === 风险敞口监控 (Gap) ===")
    print(f"当前总未对冲敞口: {total_gap:,.2f} 元")
    if total_gap > 0:
        print("提示: 正数代表【少买/裸空】，若大涨有赔付风险。")
    else:
        print("提示: 负数代表【多买/库存】，若大跌有库存贬值风险。")

# ==========================================
# 5. 🔥 智能导入 (V6.0 完美适配版)
# ==========================================
def smart_import():
    print("\n📋 [智能解析模式] 请粘贴指令文本 (Ctrl+Z/D 结束):")
    
    lines = []
    while True:
        try:
            line = input()
            if not line: break
            lines.append(line)
        except EOFError: break
    
    raw_text = "\n".join(lines)
    if len(raw_text) < 5: return
    
    print("\n🧠 正在进行API联网查询与金融风控核验...")
    parsed_list = parser.parse_mixed_text(raw_text)
    
    if not parsed_list:
        print("❌ 未识别到有效订单。"); return
        
    print(f"✅ 提取到 {len(parsed_list)} 条指令信息")
    
    df_main, df_client = core.load_db()
    
    for i, data in enumerate(parsed_list):
        print("\n" + "="*70)
        # 安全获取 is_valid，防止旧parser导致报错
        status_icon = "🟢" if data.get('is_valid', True) else "🔴"
        print(f"📄 指令 #{i+1} [单号: {data.get('order_id', 'Unknown')}] {status_icon}")
        
        client_name = data.get('client', '') or "❓缺失"
        print(f"   👤 客户: {client_name}")
        print(f"   📈 标的: {data.get('code')} -> {data.get('api_name')} (API实时核验)")
        print(f"   💰 价格: {data.get('price')} | 方向: {data.get('direction')}")
        
        # 使用 .get() 防御性获取字段，防止 KeyError
        print(f"   💵 目标本金: {data.get('amount', 0):,.2f}")
        print(f"   🔒 实收保证金: {data.get('parsed_margin', 0):,.2f} | 审计: {data.get('audit_margin', '-')}")
        print(f"   🧾 交易服务费: {data.get('parsed_fee', 0):,.2f}   | 审计: {data.get('audit_fee', '-')}")
        print(f"   ⚠️ 预警价格: {data.get('warning_price', 0)}")
        print(f"   🛑 止损价格: {data.get('stop_price', 0)}")

        if not data.get('client'):
            new_name = input("   🔴 警告: 客户名缺失，请输入: ").strip()
            if new_name: data['client'] = new_name
            else: data['client'] = "Unknown"

        new_client_row = {
            "指令单号": data.get('order_id', ''),
            "接收时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "原始文本": data.get('full_text', '')[:200],
            "客户姓名": data.get('client', ''),
            "标的代码": data.get('code', ''),
            "标的名称(API)": data.get('api_name', ''),
            "买卖方向": data.get('direction', ''),
            "指令价格": data.get('price', 0),
            "目标本金": data.get('amount', 0),
            
            # 金融核验字段 (全字段录入)
            "解析保证金": data.get('parsed_margin', 0),
            "应收保证金(5%)": data.get('amount', 0) * 0.05,
            "保证金核验": data.get('audit_margin', ''),
            "解析服务费": data.get('parsed_fee', 0),
            "应收服务费(1.3%)": data.get('amount', 0) * 0.013,
            "服务费核验": data.get('audit_fee', ''),
            "解析预警价": data.get('warning_price', 0),
            "解析止损价": data.get('stop_price', 0),
            
            "录入状态": "已录入"
        }
        df_client = pd.concat([df_client, pd.DataFrame([new_client_row])], ignore_index=True)
        print("   💾 已存入 [客户订单台账]。")

    core.save_db(df_main, df_client)
    print("\n✅ 指令入库完毕。所有数据已进入 [客户订单台账]。")
    print("   (交易总台账未受影响)")
    input("按回车返回...")

if __name__ == "__main__":
    while True:
        print("\n=== CFD 交易台 V6.0 (最终稳定版) ===")
        print("1. ⚡ 实时开仓 (紧急补单-写入总账)")
        print("2. 📜 历史补录 (手动-写入总账)")
        print("3. 🔧 匹配更正 (修总账)")
        print("4. 🔵 正常平仓")
        print("5. 🔴 爆仓/强平处理")
        print("6. 📊 每日结单 & 敞口报告")
        print("7. 📋 智能导入 (NLP -> 仅存客户表) 🔥")
        print("8. 🚪 退出")
        
        c = input("指令: ")
        if c == '1': create_order(False)
        elif c == '2': create_order(True)
        elif c == '3': update_order()
        elif c == '4': close_position(False)
        elif c == '5': close_position(True)
        elif c == '6': daily_report()
        elif c == '7': smart_import()
        elif c == '8': sys.exit()
