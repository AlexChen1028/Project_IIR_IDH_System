import os
import django
import joblib
import numpy as np
import random  # [新增] 引入 random 模組
from sklearn.isotonic import IsotonicRegression
from datetime import datetime, timedelta

# 1. 設定 Django 環境 (讓腳本能讀取資料庫)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'idh.settings') # 請確認 'idh.settings' 是您的專案設定檔名稱
django.setup()

from interface.models import Dialysis, Record, Predict
from interface.model.EBM import prepare_ebm_features_v2, check_dialysis_has_idh
from django.conf import settings

def train_iso_model():
    print("=== 開始訓練 Isotonic Regression 校準模型 ===")
    
    # 2. 載入原始 EBM 模型
    ebm_model_path = os.path.join(settings.BASE_DIR, 'interface', 'weights', 'TN_EBM_Rename.joblib')
    if not os.path.exists(ebm_model_path):
        print(f"❌ 找不到 EBM 模型: {ebm_model_path}")
        return

    print(f"Loading EBM model from: {ebm_model_path}")
    ebm_model = joblib.load(ebm_model_path)
    
    # 3. 收集訓練數據 (X: 原始預測機率, y: 真實結果)
    # 設定回溯時間 (抓過去 2000 天)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2000) 
    
    print(f"Fetching dialysis records from {start_date.date()} to {end_date.date()}...")
    
    # 抓取有足夠紀錄的透析 (排除測試資料或空資料)
    dialysis_list = Dialysis.objects.filter(
        start_time__gte=start_date,
        start_time__lte=end_date
    ).order_by('-start_time')
    
    raw_probs = [] # 原始模型預測的機率
    true_labels = [] # 真實是否發生 IDH (0 or 1)
    
    count = 0
    valid_count = 0
    
    total = dialysis_list.count()
    print(f"Total dialysis sessions found: {total}")

    # [新增] 設定抽樣率 0.06 (6%)
    SAMPLE_RATE = 0.06

    for d in dialysis_list:
        # [新增] 隨機抽樣邏輯
        # 如果資料總數夠多 (>10000)，就只取 6% 進行運算
        if total > 10000 and random.random() > SAMPLE_RATE:
            continue

        count += 1
        if count % 100 == 0:
            print(f"Processing sample {count} (Sampled from {total})...")

        try:
            # A. 取得特徵並預測原始機率
            features = prepare_ebm_features_v2(d.d_id, use_database_flag=True)
            
            # 確保特徵順序與模型一致
            feature_names = [
                '性別', '年齡', 'IDH_N_7D', 'IDH_N_28D', 'Start_SBP', 'Start_DBP',
                '脈搏', '呼吸', '開始體溫', '透析前體重(kg)', '理想體重(kg)',
                '目標脫水量(L)', 'UF_BW_Perc', '開始血液流速', '開始透析液流速',
                '透析液溫度(℃)'
            ]
            if hasattr(ebm_model, 'feature_names_in_'):
                feature_names = ebm_model.feature_names_in_
            
            feature_vector = [features[name] for name in feature_names]
            
            # 取得原始機率 (Raw Probability)
            raw_p = ebm_model.predict_proba([feature_vector])[0][1]
            
            # B. 判斷真實結果 (Ground Truth)
            # 使用 check_dialysis_has_idh 判斷該次透析是否真的有發生低血壓
            has_idh = check_dialysis_has_idh(d.d_id, use_database_flag=True)
            label = 1 if has_idh else 0
            
            raw_probs.append(raw_p)
            true_labels.append(label)
            valid_count += 1
            
        except Exception as e:
            # 忽略資料不全的案例
            continue

    print(f"Valid samples collected: {valid_count}")
    print(f"Positive cases (IDH=1): {sum(true_labels)}") # 檢查正樣本數
    print(f"Negative cases (IDH=0): {valid_count - sum(true_labels)}")
    
    if valid_count < 10:
        print("❌ 樣本數太少，無法訓練校準模型")
        return

    # 4. 訓練 Isotonic Regression
    print("Training Isotonic Regression...")
    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(raw_probs, true_labels)
    
    # 5. 儲存校準模型
    save_path = os.path.join(settings.BASE_DIR, 'interface', 'weights', 'iso_calibration.joblib')
    joblib.dump(iso_reg, save_path)
    print(f"✅ 校準模型已儲存至: {save_path}")
    
    # 6. 驗證效果 (簡單測試)
    test_probs = [0.1, 0.3, 0.5, 0.7, 0.9]
    calibrated_probs = iso_reg.transform(test_probs)
    print("\n[校準效果預覽]")
    print(f"{'原始機率':<10} -> {'校準後機率':<10}")
    print("-" * 25)
    for r, c in zip(test_probs, calibrated_probs):
        print(f"{r:<10.2f} -> {c:<10.2f}")

if __name__ == '__main__':
    train_iso_model()