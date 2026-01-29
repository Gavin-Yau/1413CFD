import pandas as pd
import os
import datetime
import warnings
import cfd_core as core

warnings.simplefilter(action='ignore', category=FutureWarning)

def load_and_clean_external_files():
    # ... (这部分保持不变，省略以节省空间，直接用上一个版本的加载逻辑即可) ...
    # 为了方便，这里直接提供完整的 reconcile_system 函数修改部分
    all_dfs = []
    current_dir = os.getcwd()
    print(f"📍 运行目录: {current_dir}")
    files_in_dir = os.listdir('.')
    target_files = []
    for f in files_in_dir:
        if "交易订单" in f and (f.endswith('.csv') or f.endswith('.CSV') or f.endswith('.xlsx')):
            target_files.append(f)
    if not target_files:
        print("\n❌ 未找到包含“交易订单”的文件！")
        return pd.DataFrame()
    print(f"🔎 锁定实盘文件: {target_files}")
    for f in target_files:
        try:
            print(f"   读取: {f} ...", end="")
            if f.endswith('.xlsx'): df = pd.read_excel(f)
            else:
                try: df = pd.read_csv(f, encoding='utf-8')
                except: 
                    try: df = pd.read_csv(f, encoding='gbk')
                    except: df = pd.read_csv(f, encoding='utf-16')
            df.columns = df.columns.str.strip()
            if 'TRS账户号' in df.columns: df = df[df['TRS账户号'] == 'T80000215']
            if '订单状态' in df.columns: df = df[df['订单状态'] == '交易完成']
            print(f"有效 {len(df)} 条")
            all_dfs.append(df)
        except Exception as e: print(f" ❌ 失败: {e}")
    if not all_dfs: return pd.DataFrame()
    merged = pd.concat(all_dfs, ignore_index=True)
    if '成交时间' in merged.columns:
        merged['成交时间'] = pd.to_datetime(merged['成交时间'])
        merged.sort_values(by='成交时间', ascending=True, inplace=True)
    subset_cols = ['成交时间', '股票代码', '方向', '成交金额']
    cols = [c for c in subset_cols if c in merged.columns]
    if cols: merged.drop_duplicates(subset=cols, inplace=True)
    return merged

def reconcile_system():
    print("\n🚀 启动实盘核对系统...")
    
    # 🔥 关键修改点：接收两个返回值，只用第一个
    df_db, df_raw_placeholder = core.load_db()
    
    if '关联外部ID' not in df_db.columns: df_db['关联外部ID'] = ""
        
    df_ext = load_and_clean_external_files()
    if df_ext.empty:
        print("❌ 无有效数据，停止。")
        return

    print("-" * 60)
    updated = 0
    new_add = 0
    closed = 0
    
    for _, row in df_ext.iterrows():
        time_str = str(row['成交时间'])
        code_str = str(row['股票代码']).split('.')[0]
        dir_str = str(row['方向'])
        amt_str = str(row['成交金额'])
        ext_id = f"{time_str}_{code_str}_{dir_str}_{amt_str}"
        
        if ext_id in df_db['关联外部ID'].values or \
           df_db['关联外部ID'].astype(str).str.contains(ext_id).any():
            continue
            
        code = code_str.zfill(6)
        name = row['股票名称']
        direction = dir_str
        try:
            fee = float(row.get('交易费用', 0))
            amt = float(row.get('成交金额', 0))
            qty = float(row.get('客户成交量', 0))
        except: continue
        if qty == 0: continue
        
        if direction == "买入":
            real_price = (amt + fee) / qty
            mask = (df_db['标的代码'] == code) & (df_db['状态'] == 'OPEN') & \
                   (df_db['关联外部ID'].isin(["", None, float('nan')]))
            candidates = df_db[mask]
            
            if not candidates.empty:
                idx = candidates.index[0]
                old = df_db.at[idx, '实际成交均价']
                print(f"🔗 [匹配] {code} {name}: 估价{old} -> 实价{real_price:.3f}")
                df_db.at[idx, '实际成交均价'] = real_price
                df_db.at[idx, '实际股数'] = qty
                df_db.at[idx, '实际持仓本金'] = qty * real_price
                df_db.at[idx, '关联外部ID'] = ext_id
                df_db.at[idx, '备注'] = str(df_db.at[idx, '备注']) + " (已核对)"
                target = df_db.at[idx, '客户目标本金']
                df_db.at[idx, '风险敞口(Gap)'] = target - (qty * real_price)
                updated += 1
            else:
                print(f"➕ [补录] {code} {name}: 买入 {qty} 股")
                day_key = str(row['成交时间']).split(' ')[0].replace('-', '')
                new_id = f"{day_key}AUTO{new_add:03d}"
                new_row = {
                    "订单编号": new_id, "状态": "OPEN", 
                    "下单时间": time_str, "平仓时间": "-",
                    "客户": "自动补录", "标的代码": code, "标的名称": name,
                    "客户目标本金": 0, "指令价格": real_price,
                    "实际成交均价": real_price, "实际股数": qty, "实际持仓本金": qty * real_price,
                    "风险敞口(Gap)": - (qty * real_price),
                    "保证金(收)": 0, "服务费(收)": 0,
                    "预警线": real_price * 0.975, "平仓线": real_price * 0.95,
                    "平仓/强平价": "-", "最终盈亏": 0, "备注": "实盘导入",
                    "关联外部ID": ext_id
                }
                df_db = pd.concat([df_db, pd.DataFrame([new_row])], ignore_index=True)
                new_add += 1

        elif direction == "卖出":
            net_price = (amt - fee) / qty
            mask = (df_db['标的代码'] == code) & (df_db['状态'] == 'OPEN')
            candidates = df_db[mask]
            if not candidates.empty:
                idx = candidates.index[0]
                print(f"🛑 [平仓] {code} {name}: 卖出 {qty} 股")
                open_price = df_db.at[idx, '实际成交均价']
                pnl = (net_price - open_price) * qty
                df_db.at[idx, '状态'] = 'CLOSED'
                df_db.at[idx, '平仓时间'] = time_str
                df_db.at[idx, '平仓/强平价'] = net_price
                df_db.at[idx, '最终盈亏'] = pnl
                old_id = str(df_db.at[idx, '关联外部ID'])
                df_db.at[idx, '关联外部ID'] = old_id + f" | 平仓:{ext_id}"
                closed += 1
            else:
                print(f"⚠️ [异常] {code} {name}: 卖出 {qty} 股，无持仓")

    # 🔥 关键修改点：保存时传入两个表 (虽然 raw 表没动，但必须传)
    core.save_db(df_db, df_raw_placeholder)
    print("-" * 60)
    print(f"✅ 完成: 修正{updated} | 补录{new_add} | 平仓{closed}")

if __name__ == "__main__":
    reconcile_system()
