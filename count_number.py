import os
import django
import time
from datetime import datetime, timedelta

# 1. 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'idh.settings')
django.setup()

from interface.models import Dialysis
# 引用判定邏輯
from interface.model.EBM import check_dialysis_has_idh

def count_all_idh():
    print("=== 開始盤點 IDH 發生總數 ===")
    
    # 設定範圍：過去 2000 天 (涵蓋您的 32 萬筆資料)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2000)
    
    print(f"搜尋範圍: {start_date.date()} ~ {end_date.date()}")
    
    # 撈出所有透析紀錄
    dialysis_list = Dialysis.objects.filter(
        start_time__gte=start_date,
        start_time__lte=end_date
    ).order_by('-start_time')
    
    total = dialysis_list.count()
    print(f"資料庫中共有 {total} 筆透析紀錄")
    
    if total == 0:
        print("❌ 找不到任何資料")
        return

    positive_count = 0  # IDH = 1
    negative_count = 0  # IDH = 0
    error_count = 0     # 資料異常
    
    start_time = time.time()
    
    # 開始逐筆檢查
    for index, d in enumerate(dialysis_list):
        # 進度條: 每 1000 筆顯示一次
        if (index + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            avg_speed = (index + 1) / elapsed
            remaining = (total - (index + 1)) / avg_speed / 60
            print(f"進度: {index + 1}/{total} | 累計 IDH: {positive_count} | 預估剩餘: {remaining:.1f} 分鐘")

        try:
            # 呼叫判定函式 (use_database_flag=True 代表優先看資料庫有沒有標記 is_idh)
            has_idh = check_dialysis_has_idh(d.d_id, use_database_flag=True)
            
            if has_idh:
                positive_count += 1
            else:
                negative_count += 1
                
        except Exception:
            error_count += 1

    # 最終報告
    print("\n" + "="*30)
    print("【盤點結果報告】")
    print(f"總筆數: {total}")
    print(f"✅ 發生 IDH (Positive): {positive_count} 筆")
    print(f"❌ 無 IDH (Negative): {negative_count} 筆")
    print(f"⚠️ 異常 (Errors): {error_count} 筆")
    
    if total > 0:
        rate = (positive_count / total) * 100
        print(f"📉 IDH 發生率: {rate:.2f}%")
    print("="*30)

if __name__ == '__main__':
    count_all_idh()