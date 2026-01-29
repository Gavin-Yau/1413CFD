import re
import datetime
import cfd_core as core

def clean_name(raw_name):
    """清洗客户名"""
    if not raw_name: return ""
    clean = re.sub(r'[【】\[\]:：\s]', '', raw_name)
    # 增加更多黑名单防止误读
    if any(x in clean for x in ["下单", "确认", "通知", "结算", "平仓", "强制", "明细", "交易"]): return ""
    if len(clean) > 10: return "" 
    return clean

def parse_mixed_text(full_text):
    """
    🧠 解析器入口 (V7.0 聚合修复版)
    """
    # 1. 调试打印：让您看到原始输入
    print(f"   🕵️ [Debug] 接收文本长度: {len(full_text)} 字符")
    full_text = full_text.replace('：', ':')
    
    # 2. 🔥 核心修复：更严格的切割逻辑
    # 旧版使用了 【交易 ，导致 【交易明细】 被切断。
    # 新版：只认准真正的订单头。
    # 含义：只有遇到 【CFD... 或 【强制... 或 开仓... 才算新的一单。
    split_pattern = r'(?=\s*【(?:CFD|强制|平仓|结算)[^】]*】|\s*开仓(?:资讯|資訊))'
    
    raw_blocks = re.split(split_pattern, full_text)
    
    clean_blocks = []
    for b in raw_blocks:
        # 必须同时包含 "订单" (或标的) 且长度足够，才算有效块
        if ("订单" in b or "标的" in b or "Code" in b) and len(b.strip()) > 20:
            clean_blocks.append(b.strip())
            
    print(f"   ⚡ [Debug] 成功聚合为 {len(clean_blocks)} 个完整订单块 (应与您的订单数一致)")
    
    parsed_orders = []
    for i, block in enumerate(clean_blocks):
        # 调试打印：看每一块是否包含了关键信息
        has_money = "目标本金" in block or "本金" in block
        print(f"      块 #{i+1}: 长度{len(block)}, 包含本金关键词? {'✅' if has_money else '❌'}")
        
        order_info = extract_single_block(block)
        if order_info:
            parsed_orders.append(order_info)
            
    return parsed_orders

def extract_single_block(text):
    data = {
        "raw_text": text[:60].replace('\n', ' ') + "...",
        "full_text": text,
        "order_id": "", "client": "", "code": "", "api_name": "",
        "price": 0.0, "amount": 0.0, "direction": "买入",
        "parsed_margin": 0.0, "parsed_fee": 0.0,
        "warning_price": 0.0, "stop_price": 0.0,
        "audit_margin": "未检测", "audit_fee": "未检测", "is_valid": True
    }
    
    # --- 0. 标题语义判定 ---
    if "强制" in text[:30] or "强平" in text[:30]: data['direction'] = "强平"
    elif "平仓" in text[:30] or "结算" in text[:30]: data['direction'] = "卖出"

    # --- 1. 订单编号 ---
    id_match = re.search(r'(?:订单编号|编号)\s*[:]\s*(\d{8,})', text)
    if id_match: data['order_id'] = id_match.group(1)
    else: data['order_id'] = datetime.datetime.now().strftime("%Y%m%d") + "TEMP"

    # --- 2. 股票代码 ---
    code_matches = re.findall(r'(?<!\d)(\d{6})(?!\d)', text)
    valid_code = False
    for c in code_matches:
        name, price = core.get_realtime_price(c)
        if name != "未知标的":
            data['code'] = c
            data['api_name'] = name
            if data['price'] == 0: data['price'] = price
            valid_code = True
            break
    if not valid_code: 
        print("      ⚠️ [Debug] 此块未找到有效股票代码，跳过")
        return None

    # --- 3. 客户名 ---
    # 针对 "客户名称：xxx" 和 "客户：xxx"
    client_match = re.search(r'(?:客户名称|客户|Client)[名]?\s*[:]\s*([^\n\r\s]+)', text)
    if client_match:
        data['client'] = clean_name(client_match.group(1).strip())

    # --- 4. 目标本金 (使用 DOTALL 跨行查找) ---
    amt_match = re.search(r'(?:目标本金|合约金额|合約金額|本金).*?[:]\s*([0-9,]+\.?\d*)', text, re.DOTALL)
    if amt_match:
        data['amount'] = float(amt_match.group(1).replace(',', ''))
    else:
        print("      ⚠️ [Debug] 未正则匹配到本金")
        
    # --- 5. 成交价格 ---
    price_match = re.search(r'(?:成交价格|开仓价格|价格|開倉價格).*?[:]\s*([0-9,]+\.?\d*)', text, re.DOTALL)
    if price_match:
        data['price'] = float(price_match.group(1).replace(',', ''))

    # --- 6. 方向 ---
    if any(k in text for k in ["卖出", "平仓", "结算"]): data['direction'] = "卖出"
    if any(k in text for k in ["强平", "强制"]): data['direction'] = "强平"

    # --- 7. 实收保证金 ---
    mar_match = re.search(r'(?:实收保证金|保证金|保證金).*?[:]\s*([0-9,]+\.?\d*)', text, re.DOTALL)
    if mar_match: data['parsed_margin'] = float(mar_match.group(1).replace(',', ''))
    
    # --- 8. 交易服务费 ---
    fee_match = re.search(r'(?:交易服务费|服务费|服務費).*?[:]\s*([0-9,]+\.?\d*)', text, re.DOTALL)
    if fee_match: data['parsed_fee'] = float(fee_match.group(1).replace(',', ''))

    # --- 9. 预警/止损 ---
    warn_match = re.search(r'(?:预警价格|预警|預警價格).*?[:]\s*([0-9,]+\.?\d*)', text, re.DOTALL)
    if warn_match: data['warning_price'] = float(warn_match.group(1).replace(',', ''))

    stop_match = re.search(r'(?:止损价格|止损|止損價格).*?[:]\s*([0-9,]+\.?\d*)', text, re.DOTALL)
    if stop_match: data['stop_price'] = float(stop_match.group(1).replace(',', ''))

    # --- 10. 审计 ---
    target = data['amount']
    if target > 0:
        exp_margin = target * 0.05
        if data['parsed_margin'] > 0:
            if abs(data['parsed_margin'] - exp_margin) < 1000:
                data['audit_margin'] = "✅ 正常"
            else:
                data['audit_margin'] = f"❌ 异常! 文:{data['parsed_margin']} 应:{exp_margin:.0f}"
                data['is_valid'] = False
        else: data['audit_margin'] = f"⚠️ 未提取到"

        fee_min, fee_max = target * 0.011, target * 0.013
        if data['parsed_fee'] > 0:
            if fee_min * 0.9 <= data['parsed_fee'] <= fee_max * 1.1:
                data['audit_fee'] = "✅ 正常"
            else:
                data['audit_fee'] = f"❌ 异常! 文:{data['parsed_fee']} (理:{fee_min:.0f}-{fee_max:.0f})"
                data['is_valid'] = False
        else: data['audit_fee'] = f"⚠️ 未提取到"
        
    return data
