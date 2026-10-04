# interface/model/EBM.py
import os
import joblib
import traceback
from decimal import Decimal
from django.conf import settings
from interface.models import Dialysis, Record, Patient
from datetime import timedelta
# 僅在需要比對加密 ID 或處理加密姓名時使用
from interface.utils import CryptoManager 

def check_dialysis_has_idh(dialysis_id, use_database_flag=True):
    """
    判斷某次透析是否有發生 IDH
    """
    try:
        dialysis = Dialysis.objects.get(d_id=dialysis_id)
        records = Record.objects.filter(d_id=dialysis).order_by('record_time')
        
        if records.count() == 0:
            return False
        
        # 模式 1: 使用資料庫標記
        if use_database_flag:
            if records.filter(is_idh=True).exists():
                return True
        
        # 模式 2: Nadir90/100 邏輯判斷
        start_sbp = float(dialysis.start_SBP) if dialysis.start_SBP else None
        if start_sbp is None or start_sbp < 50:
            return False
        
        valid_sbp_records = [float(r.SBP) for r in records if float(r.SBP) >= 50]
        if not valid_sbp_records:
            return False
        
        threshold = 90 if start_sbp < 160 else 100
        return any(sbp < threshold for sbp in valid_sbp_records)
        
    except Exception as e:
        print(f"[EBM] check_dialysis_has_idh Error: {e}")
        return False

def calculate_idh_count_with_dual_mode(patient_id, current_start_time, days=7, use_database_flag=True):
    """
    計算該病人在過去 N 天內發生 IDH 的次數 (不含當天)
    """
    try:
        end_date = current_start_time.date()
        start_date = end_date - timedelta(days=days)
        
        # 由於 patient_id (FK) 在資料庫中是以加密形式儲存，此處直接進行過濾即可正確比對
        past_dialysis_list = Dialysis.objects.filter(
            p_id=patient_id,
            start_time__date__gte=start_date,
            start_time__date__lt=end_date
        )
        
        idh_count = 0
        for past_dialysis in past_dialysis_list:
            if check_dialysis_has_idh(past_dialysis.d_id, use_database_flag=use_database_flag):
                idh_count += 1
        return idh_count
    except Exception as e:
        print(f"[EBM] calculate_idh_count Error: {e}")
        return 0

def prepare_ebm_features_v2(dialysis_id, use_database_flag=True):
    """
    準備 EBM Model 所需的 16 個特徵
    """
    dialysis = Dialysis.objects.get(d_id=dialysis_id)
    patient = dialysis.p_id
    
    latest_record = Record.objects.filter(d_id=dialysis).order_by('-record_time').first()
    
    if latest_record:
        pulse_value = int(latest_record.pulse)
        breath_value = float(latest_record.breath)
        dialyse_temp_value = float(latest_record.dialyse_temperature)
    else:
        pulse_value = 80
        breath_value = 18.0
        dialyse_temp_value = float(dialysis.start_temperature) if dialysis.start_temperature else 36.5
    
    before_weight = float(dialysis.before_weight) if dialysis.before_weight else 0.0
    expect_dehydration = float(dialysis.expect_dehydration) if dialysis.expect_dehydration else 0.0
    uf_bw_perc_value = (expect_dehydration / before_weight) if before_weight > 0 else 0.0
    
    # 歷史 IDH 次數計算 (patient.p_id 已為加密狀態)
    idh_7d = calculate_idh_count_with_dual_mode(
        patient.p_id, dialysis.start_time, days=7, use_database_flag=use_database_flag
    )
    idh_28d = calculate_idh_count_with_dual_mode(
        patient.p_id, dialysis.start_time, days=28, use_database_flag=use_database_flag
    )
    
    # 性別判定：因 gender 為明文，直接比對即可
    gender_val = 1 if patient.gender == '男' else 0
    
    features = {
        '性別': gender_val,
        '年齡': int(dialysis.age),
        'IDH_N_7D': idh_7d,
        'IDH_N_28D': idh_28d,
        'Start_SBP': float(dialysis.start_SBP) if dialysis.start_SBP else 0.0,
        'Start_DBP': int(dialysis.start_DBP) if dialysis.start_DBP else 0,
        '脈搏': pulse_value,
        '呼吸': breath_value,
        '開始體溫': float(dialysis.start_temperature) if dialysis.start_temperature else 36.5,
        '透析前體重(kg)': before_weight,
        '理想體重(kg)': float(dialysis.ideal_weight) if dialysis.ideal_weight else 0.0,
        '目標脫水量(L)': expect_dehydration,
        'UF_BW_Perc': uf_bw_perc_value,
        '開始血液流速': float(dialysis.start_blood_speed) if dialysis.start_blood_speed else 0.0,
        '開始透析液流速': float(dialysis.start_flow_speed) if dialysis.start_flow_speed else 0.0,
        '透析液溫度(℃)': dialyse_temp_value,
    }
    return features

def predict_idh_ebm(dialysis_id, use_database_flag=False):
    """
    使用 EBM Model 預測 IDH 風險（直接回傳原始機率，不做 Isotonic 校準）
    """
    try:
        # 1. 載入 EBM 模型
        model_path = os.path.join(settings.BASE_DIR, 'interface', 'weights', 'TN_EBM_Rename.joblib')
        if not os.path.exists(model_path):
            print(f"[EBM] Model file not found at: {model_path}")
            return 0.0

        model = joblib.load(model_path)
        features = prepare_ebm_features_v2(dialysis_id, use_database_flag)
        
        feature_names = [
            '性別', '年齡', 'IDH_N_7D', 'IDH_N_28D', 'Start_SBP', 'Start_DBP',
            '脈搏', '呼吸', '開始體溫', '透析前體重(kg)', '理想體重(kg)',
            '目標脫水量(L)', 'UF_BW_Perc', '開始血液流速', '開始透析液流速',
            '透析液溫度(℃)'
        ]
        
        if hasattr(model, 'feature_names_in_'):
            feature_names = model.feature_names_in_
        
        feature_vector = [features[name] for name in feature_names]
        
        # 2. 取得原始機率 (Raw Probability) — 不再做 Isotonic 校準
        raw_proba = model.predict_proba([feature_vector])[0][1]
        
        print(f"[EBM] Dialysis {dialysis_id} | Raw Probability: {raw_proba:.4f}")
        
        return float(raw_proba)
        
    except Exception as e:
        print(f"[EBM] Error predicting for dialysis {dialysis_id}: {str(e)}")
        return 0.0
