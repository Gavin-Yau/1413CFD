import pandas as pd
import time
import datetime
import os
import sys
import cfd_core as core

# 清屏命令适配
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def monitor_system():
    print("📡 CFD 风控雷达系统启动...")
    print("   正在连接交易所 API...")
    
    while True:
        try:
            # 1. 加载最新的实盘台账
            # 注意：监控程序只关心【交易总台账】里的 OPEN 持仓
            df_main, _ = core.load_db()
            
            if df_main.empty:
                print("💤 暂无实盘数据，等待中...")
                time.sleep(10)
                continue

            # 2. 筛选出正在持仓的订单 (状态=OPEN)
            opens = df_main[df_main['状态'] == 'OPEN'].copy()
            
            if opens.empty:
                clear_screen()
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ 当前空仓，无风险。")
                time.sleep(10)
                continue
            
            # 3. 开始扫描
            clear_screen()
            print(f"╔{'═'*78}╗")
            print(f"║ 📡 CFD 实时风控雷达 (V7.0)   刷新时间: {datetime.datetime.now().strftime('%H:%M:%S')}   持仓数: {len(opens)}     ║")
            print(f"╠{'═'*78}╣")
            print(f"║ {'单号':<14} {'标的':<8} {'成本':<7} {'现价':<7} {'盈亏%':<7} {'状态':<20} ║")
            print(f"╠{'═'*78}╣")
            
            total_float_pnl = 0
            alert_count = 0
            
            for _, row in opens.iterrows():
                code = str(row['标的代码'])
                name = str(row['标的名称'])
                cost = float(row['实际成交均价'])
                shares = float(row['实际股数'])
                warn_price = float(row['预警线'])
                stop_price = float(row['平仓线'])
                
                # 获取实时价格
                api_name, curr_price = core.get_realtime_price(code)
                
                # 如果停牌或获取失败，用成本价暂代，避免报错
                if curr_price == 0: curr_price = cost
                
                # 计算浮动盈亏
                pnl_val = (curr_price - cost) * shares
                pnl_pct = (curr_price - cost) / cost * 100
                total_float_pnl += pnl_val
                
                # 判断风险状态
                status = "✅ 正常"
                
                # 逻辑：如果是做多 (目前系统默认做多逻辑)
                if curr_price <= stop_price:
                    status = "🔴 触发止损线！！！"
                    alert_count += 1
                elif curr_price <= warn_price:
                    status = "⚠️ 触发预警线"
                    alert_count += 1
                elif pnl_pct > 0:
                    status = "🟢 盈利中"
                    
                # 打印单行
                # 格式化输出，确保对齐
                print(f"║ {row['订单编号']:<14} {name:<8} {cost:<7.2f} {curr_price:<7.2f} {pnl_pct:>6.2f}%  {status:<20} ║")

            print(f"╠{'═'*78}╣")
            print(f"║ 📊 实时总浮盈亏: {total_float_pnl:+,.2f} 元 {' '*45}║")
            print(f"╚{'═'*78}╝")
            
            if alert_count > 0:
                # Windows发出蜂鸣报警
                print("\n🚨 警报：检测到风险订单，请立即处理！\a")
            
            # 4. 休眠 (避免请求太快被新浪封IP)
            # 建议设置为 5-10 秒
            time.sleep(8)
            
        except Exception as e:
            print(f"❌ 监控报错: {e}")
            print("   (3秒后重试...)")
            time.sleep(3)

if __name__ == "__main__":
    monitor_system()
