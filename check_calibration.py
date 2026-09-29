import os
import joblib
import django
from django.conf import settings

# 1. 設定 Django 環境 (為了取得 settings.BASE_DIR 路徑)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'idh.settings')
django.setup()

def check_existing_model():
    # 2. 指定模型路徑
    model_path = os.path.join(settings.BASE_DIR, 'interface', 'weights', 'iso_calibration.joblib')
    
    # 3. 檢查檔案是否存在
    if not os.path.exists(model_path):
        print(f"❌ 找不到校準模型檔案！")
        print(f"路徑: {model_path}")
        print("請確認您至少已經完整執行過一次 train_calibration.py")
        return

    # 4. 載入模型 (不需重新訓練)
    print(f"✅ 正在讀取模型: {model_path}")
    try:
        iso_reg = joblib.load(model_path)
    except Exception as e:
        print(f"❌ 模型讀取失敗: {e}")
        return

    # 5. 輸入測試數據 (您可以自由增加想要看的機率點)
    test_probs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
    
    # 6. 進行轉換
    calibrated_probs = iso_reg.transform(test_probs)

    # 7. 顯示高精準度結果 (.6f 代表小數點後 6 位)
    print("\n[現有模型校準詳細數據]")
    print(f"{'原始 EBM 機率':<15} -> {'校準後真實機率':<15}")
    print("-" * 40)
    
    for r, c in zip(test_probs, calibrated_probs):
        # 這裡設定 .6f 看得更細
        print(f"{r:<15.2f} -> {c:<15.6f}")

if __name__ == '__main__':
    check_existing_model()