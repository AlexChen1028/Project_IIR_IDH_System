from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import json
import datetime
import os
import csv
from datetime import datetime, timedelta
from django.conf import settings
from interface.models import Patient, Dialysis, Record, Feedback, Predict, Warnings, Nurse, Nurse_Record
from django.core import serializers
from django.db.models import Max
from scripts.fetch_API import fetchData
from scripts.DBbuilder import splitCSV
from scripts.load_data import saveData
from decimal import Decimal
import numpy as np
from openpyxl import Workbook
from django.views.decorators.csrf import csrf_exempt
# import joblib  # 115/01/06 update for isotonic regression model loading

# 移除原本的：from interface.model.prediction import predict_idh
from interface.model.prediction import predict_idh

from interface.utils import CryptoManager # 115/01/14 update for encryption/decryption

# 115/02/25 update 用來算標準差跟抓api資料的函式
import math
import requests

# === [NEW] 新版 LangChain 引用 (LCEL 架構) ===
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- LLM 設定 ---
LLM_MODEL = "gpt-oss:120b"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

HOSPITAL_API_URL = os.environ.get("HOSPITAL_API_URL", "http://localhost/php/dialysislist.php")

# Create your views here.

b_area = ['B25', 'B23', 'B26', 'B22', 'B27', 'B21']
a_area = ['A08', 'A09', 'A10', 'A11', 'A16', 'A15', 'A13', 'A12']
left_area = ['A01', 'A02', 'A03', 'PRN', 'A05', 'A06', 'A07']
bottom_area = ['B28', 'B29', 'B20', 'B19', 'B18', 'B17']

def get_time():
    now = True
    # now = True #push要改True
    if now:
        time = datetime.now()
    else:
        time = datetime(2025, 12, 1, 8, 30, 0)
        # time = datetime(2023, 9, 23, 10, 43, 0)
    return time

# === 115/02/25 [新增整段函式] 專門用來讀取本地的歷史 CSV 並計算平均與標準差 ===
# def fetch_history_stats_local(real_case_number, current_date_str):
#     """
#     從本地端 decoded CSV 讀取前 9 次透析歷史，並計算平均與標準差 (同天算一次)
#     """
#     # 對應您的檔案命名規則 (例如: history_<case_number>.csv)
#     file_path = os.path.join(settings.BASE_DIR, 'interface', 'data', f'history_{real_case_number}.csv')
    
#     if not os.path.exists(file_path):
#         print(f"⚠️ 找不到歷史資料檔: {file_path}")
#         return None

#     def s_float(val):
#         try: return float(val)
#         except: return None

#     daily_data = {}
    
#     try:
#         with open(file_path, 'r', encoding='utf-8-sig') as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 dt_str = row.get('透析開始時間', '')
#                 if not dt_str: continue
                
#                 date_key = dt_str[:10] # 取 YYYY-MM-DD
                
#                 # 只取「今天以前」的紀錄
#                 if date_key >= current_date_str:
#                     continue
                    
#                 if date_key not in daily_data:
#                     daily_data[date_key] = {
#                         'pre_w': s_float(row.get('透析前體重(kg)')),
#                         'end_w': s_float(row.get('結束體重(kg)')),
#                         'uf': s_float(row.get('實際脫水量(L)')),
#                         'sbp_list': [],
#                         'bf_list': [],
#                         'df_list': []
#                     }
                    
#                 # 收集血壓與流速 (只要有數值就納入)
#                 # 兼容不同可能的欄位名稱
#                 sbp = s_float(row.get('血壓(收縮)')) or s_float(row.get('Start_SBP')) or s_float(row.get('End_SBP'))
#                 if sbp and sbp > 0: daily_data[date_key]['sbp_list'].append(sbp)
                
#                 bf = s_float(row.get('血流速(ml/min)')) or s_float(row.get('開始血液流速'))
#                 if bf and bf > 0: daily_data[date_key]['bf_list'].append(bf)
                
#                 df = s_float(row.get('透析液流速(ml/min)')) or s_float(row.get('開始透析液流速'))
#                 if df and df > 0: daily_data[date_key]['df_list'].append(df)

#     except Exception as e:
#         print(f"讀取 CSV 發生錯誤: {e}")
#         return None

#     # 將日期由新到舊排序，取最近的 9 次透析
#     sorted_dates = sorted(daily_data.keys(), reverse=True)[:9]
#     if not sorted_dates:
#         return None

#     # 計算各項指標
#     end_weights = []
#     ufs = []
#     uf_percs = []
#     idh_count = 0
#     all_bfs = []
#     all_dfs = []

#     for d in sorted_dates:
#         data = daily_data[d]
#         if data['end_w'] is not None: end_weights.append(data['end_w'])
#         if data['uf'] is not None: ufs.append(data['uf'])
#         if data['uf'] is not None and data['pre_w'] and data['pre_w'] > 0:
#             uf_percs.append((data['uf'] / data['pre_w']) * 100)
            
#         # 判斷當次是否有發生低血壓 (只要該天任一筆紀錄 SBP < 90 就算一次)
#         if any(sbp < 90 for sbp in data['sbp_list']):
#             idh_count += 1
            
#         all_bfs.extend(data['bf_list'])
#         all_dfs.extend(data['df_list'])

#     # 內部計算平均與標準差的輔助函式
#     def calc_mean_std(values):
#         if not values: return 0, 0
#         n = len(values)
#         mean = sum(values) / n
#         if n < 2: return mean, 0
#         variance = sum((x - mean) ** 2 for x in values) / (n - 1) # 樣本標準差
#         return mean, math.sqrt(variance)

#     mean_end_w, std_end_w = calc_mean_std(end_weights)
#     mean_uf, std_uf = calc_mean_std(ufs)
#     mean_uf_perc, _ = calc_mean_std(uf_percs)

#     return {
#         'count': len(sorted_dates),
#         'idh_count': idh_count,
#         'avg_end_w': mean_end_w,
#         'sd_end_w': std_end_w,
#         'avg_uf': mean_uf,
#         'sd_uf': std_uf,
#         'max_uf': max(ufs) if ufs else 0,
#         'avg_uf_perc': mean_uf_perc,
#         'bf_min': int(min(all_bfs)) if all_bfs else 0,
#         'bf_max': int(max(all_bfs)) if all_bfs else 0,
#         'df_min': int(min(all_dfs)) if all_dfs else 0,
#         'df_max': int(max(all_dfs)) if all_dfs else 0,
#     }

# === 115/02/25 [擴充版] 歷史資料 12 次精準計算 ===
def fetch_history_stats(real_case_number, current_date_str):
    records_to_process = []
    headers = [
        "ID", "姓名", "性別", "出生年月日", "年齡", "透析次數(本院)", 
        "透析開始時間", "透析結束時間", "紀錄時間", "透析機編號", "床位", 
        "體溫", "開始體溫", "透析前體重(kg)", "理想體重(kg)", "目標脫水量(L)", 
        "輸液量(L)", "食物重量(kg)", "預估脫水量(L)", "設定脫水量(L)", "結束體重(kg)", 
        "實際脫水量(L)", "血壓(收縮)", "血壓(舒張)", "End_SBP", "End_DBP", 
        "透析模式", "透析器", "開始透析液流速", "開始血液流速", "透析液Ca：3.0", 
        "傳導度：13.9", "血管通路", "Heparin", "ESA", "透析器凝血情況", 
        "Start_SBP", "Start_DBP", "脈搏", "呼吸", "血流速(ml/min)", 
        "透析液流速(ml/min)", "靜脈壓(mmHg)", "透析液壓(mmHg)", "膜上壓(mmHg)", 
        "脫水速率", "累積量", "透析液溫度(℃)", "肝素注射量(ml/hr)", "沖水量(L)", 
        "確認血管通路", "label_90", "label_40", "time_step"
    ]

    # --- 判斷資料來源 ---

    end_date = current_date_str
    start_date = (datetime.strptime(current_date_str, "%Y-%m-%d") - timedelta(days=45)).strftime("%Y-%m-%d")
    api_url = f"{HOSPITAL_API_URL}?case_number={real_case_number}&start_date={start_date}&end_date={end_date}"
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            api_records = res_json.get('data_list', [])
            if api_records:
                shared_csv_path = os.path.join(settings.BASE_DIR, 'interface', 'data', 'all_patients_history.csv')
                file_exists = os.path.exists(shared_csv_path)
                with open(shared_csv_path, 'a', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists: writer.writerow(headers)
                    separator_row = [f"=== 新增抓取 ===", f"Case: {real_case_number}", f"Start: {start_date}", f"End: {end_date}"]
                    separator_row.extend([""] * (len(headers) - len(separator_row)))
                    writer.writerow(separator_row)
                    for r in api_records:
                        row_list = list(r)
                        if len(row_list) < len(headers): row_list.extend([""] * (len(headers) - len(row_list)))
                        elif len(row_list) > len(headers): row_list = row_list[:len(headers)]
                        writer.writerow(row_list)
                        records_to_process.append(dict(zip(headers, row_list)))
    except Exception as e:
        print(f"❌ API 請求失敗: {e}")

    if not records_to_process:
        return None

    def s_float(val):
        try: return float(val)
        except: return None

    daily_data = {}
    for row in records_to_process:
        dt_str = row.get('透析開始時間', '')
        if not dt_str: continue
        
        date_key = dt_str[:10]
        if date_key >= current_date_str: continue
            
        if date_key not in daily_data:
            daily_data[date_key] = {
                'pre_w': s_float(row.get('透析前體重(kg)')),
                'end_w': s_float(row.get('結束體重(kg)')),
                'uf': s_float(row.get('實際脫水量(L)')),
                'sbp_list': [],
                'start_sbp': None,
                'vp_list': [],
                'bf_list': [],
                'df_list': [],
                'esa': str(row.get('ESA', '')),
                'coag': str(row.get('透析器凝血情況', ''))
            }
        
        # 紀錄透析前收縮壓 (第一筆)
        if daily_data[date_key]['start_sbp'] is None:
            daily_data[date_key]['start_sbp'] = s_float(row.get('Start_SBP')) or s_float(row.get('血壓(收縮)'))
            
        sbp = s_float(row.get('血壓(收縮)')) or s_float(row.get('Start_SBP')) or s_float(row.get('End_SBP'))
        if sbp and sbp > 0: daily_data[date_key]['sbp_list'].append(sbp)
        
        vp = s_float(row.get('靜脈壓(mmHg)'))
        if vp and vp > 0: daily_data[date_key]['vp_list'].append(vp)
        
        bf = s_float(row.get('血流速(ml/min)')) or s_float(row.get('開始血液流速'))
        if bf and bf > 0: daily_data[date_key]['bf_list'].append(bf)
        
        df = s_float(row.get('透析液流速(ml/min)')) or s_float(row.get('開始透析液流速'))
        if df and df > 0: daily_data[date_key]['df_list'].append(df)

    # 取最近 12 次
    sorted_dates = sorted(daily_data.keys(), reverse=True)[:12]
    if not sorted_dates: return None

    end_weights, ufs, uf_percs, all_bfs, all_dfs, start_sbps, all_vps, idwg_list = [], [], [], [], [], [], [], []
    idh_count, darb_count, epo_count = 0, 0, 0
    abnormal_records = []

    for i, d in enumerate(sorted_dates):
        data = daily_data[d]
        if data['end_w'] is not None: end_weights.append(data['end_w'])
        if data['uf'] is not None: ufs.append(data['uf'])
        if data['uf'] and data['pre_w'] and data['pre_w'] > 0:
            uf_percs.append((data['uf'] / data['pre_w']) * 100)
        if data['start_sbp']: start_sbps.append(data['start_sbp'])
        
        # IDWG 計算 (當次透前 - 上次透後)
        if i < len(sorted_dates) - 1:
            prev_d = sorted_dates[i+1]
            if data['pre_w'] and daily_data[prev_d]['end_w']:
                idwg_list.append(data['pre_w'] - daily_data[prev_d]['end_w'])
                
        if any(sbp < 90 for sbp in data['sbp_list']): idh_count += 1
            
        all_bfs.extend(data['bf_list'])
        all_dfs.extend(data['df_list'])
        all_vps.extend(data['vp_list'])
        
        # ESA 計算
        esa_str = data['esa'].lower()
        if 'darbepoetin' in esa_str: darb_count += 1
        if 'epoetin' in esa_str: epo_count += 1
            
        # 異常紀錄收集
        coag = data['coag'].lower()
        if coag and coag not in ['clear', '無', '-', '']:
            abnormal_records.append(f"{d[5:]} 管路凝血({data['coag']})")

    def calc_mean_std(values):
        if not values: return 0, 0
        n = len(values)
        mean = sum(values) / n
        if n < 2: return mean, 0
        return mean, math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1))

    mean_end_w, std_end_w = calc_mean_std(end_weights)
    mean_uf, std_uf = calc_mean_std(ufs)
    mean_idwg, std_idwg = calc_mean_std(idwg_list)
    mean_uf_perc, _ = calc_mean_std(uf_percs)
    
    last_history_end_w = daily_data[sorted_dates[0]]['end_w'] if sorted_dates else None

    return {
        'count': len(sorted_dates),
        'idh_count': idh_count,
        'avg_end_w': mean_end_w, 'sd_end_w': std_end_w,
        'avg_uf': mean_uf, 'sd_uf': std_uf,
        'max_uf': max(ufs) if ufs else 0,
        'avg_uf_perc': mean_uf_perc,
        'avg_start_sbp': np.mean(start_sbps) if start_sbps else 0,
        'avg_vp': np.mean(all_vps) if all_vps else 0,
        'avg_idwg': mean_idwg, 'sd_idwg': std_idwg,
        'bf_min': int(min(all_bfs)) if all_bfs else 0,
        'bf_max': int(max(all_bfs)) if all_bfs else 0,
        'df_min': int(min(all_dfs)) if all_dfs else 0,
        'df_max': int(max(all_dfs)) if all_dfs else 0,
        'darb_count': darb_count, 'epo_count': epo_count,
        'abnormal': "、".join(abnormal_records) if abnormal_records else "無",
        'last_history_end_w': last_history_end_w
    }

def get_llm_summary(bed, patient_id, idh_prob=0):
    """
    [智能透析統整] - LLM 填空版 (支援 UFR, IDWG, 靜脈壓與 12 次歷史 + 結尾今日詳細紀錄 / 純文字版)
    """
    try:
        # 1. 轉換風險文字
        risk_text = "低"
        if idh_prob >= 2: risk_text = "高"
        elif idh_prob >= 1: risk_text = "中"
        
        target_search_id = str(patient_id).strip()
        encrypted_search_id = CryptoManager.encrypt_deterministic(target_search_id)
        real_case_number = CryptoManager.decrypt_deterministic(target_search_id) or target_search_id 
            
        simulation_time = get_time()
        target_date_str = simulation_time.strftime("%Y-%m-%d")
        
        csv_path = os.path.join(settings.BASE_DIR, 'interface', 'data', 'dialysis.csv')
        if not os.path.exists(csv_path):
            csv_path = os.path.join(settings.BASE_DIR, 'interface', 'data', 'temp.csv')
            if not os.path.exists(csv_path): return "查無資料檔"

        today_records = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    csv_p_id = (row.get('case_number') or row.get('ID') or '').strip()
                    if csv_p_id in [encrypted_search_id, target_search_id]:
                        if row.get('透析開始時間', '').startswith(target_date_str):
                            today_records.append(row)
        except Exception as e: return f"讀取 CSV 錯誤: {e}"

        if not today_records: return f"無 {target_date_str} 的透析資料"
        
        found_data = today_records[-1] # 最後一筆當作結束狀態
        first_data = today_records[0]  # 第一筆當作開始狀態

        stats = fetch_history_stats(real_case_number, target_date_str)
        
        # === 計算今日數據 ===
        def s_float_local(val):
            try: return float(val)
            except: return None

        today_target_uf = s_float_local(found_data.get('設定脫水量(L)')) or s_float_local(found_data.get('目標脫水量(L)')) or s_float_local(found_data.get('實際脫水量(L)'))
        today_pre_w = s_float_local(found_data.get('透析前體重(kg)'))
        today_start_sbp = s_float_local(first_data.get('Start_SBP')) or s_float_local(first_data.get('血壓(收縮)'))
        
        # [修改] 直接抓取 CSV 該筆紀錄中「靜脈壓(mmHg)」的數值，不再算整天平均
        today_vp = s_float_local(found_data.get('靜脈壓(mmHg)')) or 0
        
        today_ufr = 0
        if today_target_uf and today_pre_w:
            today_ufr = (today_target_uf * 1000) / today_pre_w / 4.0

        today_idwg = 0
        if today_pre_w and stats and stats['last_history_end_w']:
            today_idwg = today_pre_w - stats['last_history_end_w']

        # === 準備給 LLM 的「參考小抄」 ===
        if stats:
            uf_diff = (today_target_uf - stats['avg_uf']) if today_target_uf else 0
            uf_status = "高" if uf_diff > stats['sd_uf'] else ("低" if uf_diff < -stats['sd_uf'] else "等")
            
            ufr_status = "是" if today_ufr > 10 else "否"
            
            sbp_diff = (today_start_sbp - stats['avg_start_sbp']) if today_start_sbp else 0
            sbp_status = "高" if sbp_diff > 0 else "低"
            
            idwg_status = "高" if today_idwg > stats['avg_idwg'] else "低"
            
            vp_diff = today_vp - stats['avg_vp']
            vp_status = "高" if vp_diff > 0 else "低"

            data_context = f"""
            [今日比對小抄]
            脫水量差：{abs(uf_diff):.2f} L，{uf_status}於標準差
            UFR：{today_ufr:.1f} ml/kg/hr，{ufr_status}大於危險閾值
            今日透析前收縮壓：{today_start_sbp or '_'} mmHg，較歷史平均{sbp_status} {abs(sbp_diff):.1f} mmHg
            今日IDWG：{today_idwg:.1f} kg，{idwg_status}於平均
            今日平均靜脈壓：{today_vp:.1f} mmHg，{vp_status}於平均 ({vp_diff:+.1f} mmHg)
            
            [前12次歷史統計小抄]
            透析中低血壓次數：{stats['idh_count']}
            平均脫水量：{stats['avg_uf']:.1f} kg +/- {stats['sd_uf']:.2f}
            平均透析前收縮壓：{stats['avg_start_sbp']:.1f} mmHg
            平均透析間體重增加(IDWG)：{stats['avg_idwg']:.1f} kg +/- {stats['sd_idwg']:.2f}
            平均透析後體重：{stats['avg_end_w']:.1f} kg +/- {stats['sd_end_w']:.2f}
            平均脫水佔體重百分比：{stats['avg_uf_perc']:.1f} %
            最大脫水量：{stats['max_uf']:.1f} kg
            Blood flow range：{stats['bf_min']} ~ {stats['bf_max']}
            Dialysate flow range：{stats['df_min']} ~ {stats['df_max']}
            平均靜脈壓：{stats['avg_vp']:.1f} mmHg
            ESA總劑量：Darbepoetin α 20mcg {stats['darb_count']} 支, Epoetin α inj 2000IU {stats['epo_count']} 支
            過去異常紀錄：{stats['abnormal']}
            
            [今日原始數據]
            透析模式: {found_data.get('透析模式', '無')}
            透析液流速: {found_data.get('開始透析液流速', '_')}
            血液流速: {found_data.get('開始血液流速', '_')}
            Heparin: {found_data.get('Heparin', '無')}
            透析前體重: {today_pre_w or '_'}
            結束體重: {found_data.get('結束體重(kg)', '_')}
            理想體重: {found_data.get('理想體重(kg)', '_')}
            設定脫水量: {today_target_uf or '_'}
            實際脫水量: {found_data.get('實際脫水量(L)', '_')}
            ESA: {found_data.get('ESA', '無')}
            開始血壓: {first_data.get('Start_SBP', '_')}/{first_data.get('Start_DBP', '_')}
            結束血壓: {found_data.get('End_SBP', '_')}/{found_data.get('End_DBP', '_')}
            凝血情況: {found_data.get('透析器凝血情況', '無')}
            """
        else:
            data_context = "[資料小抄] 無歷史資料。"

        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=LLM_MODEL, temperature=0.1, base_url=OLLAMA_BASE_URL)

        # 把 <div> 跟 <br> 徹底拔除，只留純文字與換行符號
        template_str = """
你是一位專業的醫療護理助手。請根據下方提供的【資料小抄】，【嚴格】照著下方的【輸出格式】把資料填進去。
絕對不要加上任何前言、結語或「這是一份摘要」等廢話，只要輸出填寫好的格式內容。

【資料小抄】
{data_context}
預測風險：{risk_text} 機率 (Risk Score: {idh_prob})

【請直接輸出以下格式內容，並把括號替換為小抄裡的真實數值】
[智能透析統整]
低血壓預測：{risk_text} 機率。(Risk score : {idh_prob})

本日透析與歷史比較：
脫水量差 = [填入脫水量差] L， [高/低/等] 於標準差 (今日目標脫水量 - 平均脫水量)
本日預估脫水速率 (UFR) = [填入UFR] ml/kg/hr， [是/否] 大於危險閾值 (>10 ml/kg/hr)。
本日透析前收縮壓 = [填入今日收縮壓] mmHg， 較歷史平均 [高/低] [填入差異] mmHg。
本日IDWG = [填入今日IDWG] kg, [高/低] 於平均 IDWG
管路壓力狀態：靜脈壓 = {today_vp} mmHg, [高/低] 於平均 ([+/- 差異] mmHg)

前12次透析摘要：
透析中低血壓次數：[填入次數] (nadir 90)
平均脫水量：[填入平均] kg +/- [填入標準差]
平均透析前收縮壓 = [填入平均] mmHg
平均透析間體重增加 (IDWG) = [填入平均] kg +/- [填入標準差]
平均透析後體重 = [填入平均] kg +/- [填入標準差]
平均脫水佔體重百分比：[填入百分比] %
最大脫水量：[填入最大值] kg
Blood flow range ：[最小值] ~ [最大值]
Dialysate flow range：[最小值] ~ [最大值]
平均靜脈壓 = [填入平均] mmHg 
ESA 總劑量： Darbepoetin α 20mcg [填入支數] 支, Epoetin α inj 2000IU [填入支數] 支

(過去幾次是否有「上針困難」、「透析後止血時間大於 20 分鐘」或「管路內凝血 (Clotting)」的紀錄：[填入異常紀錄，若無則填無])

--------------------------------------------
日期: {target_date}
透析模式: [填寫今日透析模式]
今日透析設定與醫囑: 採一般 Mode, 
透析液流速[數值]ml/min, 
血液流速[數值]ml/min, 
heparin [填入數據內容]。
今日脫水狀況: 今日體重[數值]kg, 
乾體重(理想體重)[數值]kg。
設定脫水量[數值]kg, 
實際脫水[數值]kg。
藥物給予: [填入 ESA 內容，若無則填無]。
低血壓預測: 本次透析中低血壓預測為 {risk_text} 機率 (Risk Score: {idh_prob})。
透析過程: 開始血壓 [SBP]/[DBP] mmHg; 
結束血壓 [SBP]/[DBP] mmHg。
異常事件紀錄: [若凝血情況不為 clear 請註記，否則填無]。
"""

        prompt = ChatPromptTemplate.from_template(template_str)
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser
        
        # 取得純文字並直接回傳
        response = chain.invoke({
            "data_context": data_context.strip(),
            "risk_text": risk_text,
            "idh_prob": idh_prob,
            "target_date": target_date_str,
            "today_vp": f"{today_vp:.1f}"  # <=== 加上這一行，把 CSV 數據直接填入
        })
        
        return response

    except Exception as e:
        return f"摘要生成失敗: {str(e)}"

def index(request, area="dashboard"):
    time = get_time()
    if area == "dashboard" and time.minute % 3 == 0: 
        corn_job()
    if area == 'Z':
        return render(request, 'nurseAreaAdjust.html')
    if area == 'Y':
        if request.method == 'GET':
            nurseList = list(Nurse.objects.all().values())
            return render(request, 'nurseAreaSearch.html', {
                "home": True,
                "patients": [],
                "chart": json.dumps([]),
                'nurseList': nurseList,
            })
    patients = get_patients()
    if all(all(i['id'] == '---' for i in p) for p in list(patients.values())):
        corn_job()
        return render(request, 'index.html', {
            "home": True,
            "area": area,
            "a_patients": patients["a_patients"],
            "b_patients": patients["b_patients"],
            "left_patients": patients["left_patients"],
            "bottom_patients": patients["bottom_patients"],
            "high_risk_patients": patients.get("high_risk_patients", []),
        })
    return render(request, 'index.html', {
        "home": True,
        "area": area,
        "a_patients": patients["a_patients"],
        "b_patients": patients["b_patients"],
        "left_patients": patients["left_patients"],
        "bottom_patients": patients["bottom_patients"],
        "high_risk_patients": patients.get("high_risk_patients", []),
    })

# 護理師專區
def NurseAreaSearch(request, nurseId, bedList):
    if bedList != "emp":
        patients = get_nurse_patients(bedList.split("-"))
    else:
        patients = []
    nurseList = list(Nurse.objects.all().values())
    return render(request, 'nurseAreaSearch.html', {
        'nurseList': nurseList,
        "nurseId": nurseId,
        "home": True,
        "patients": patients["nurse_patients"] if len(patients) > 0 else [],
        "chart": json.dumps([]),
    })

def NurseAreaAdjust(request, nurseId):
    if nurseId == "emp":
        nurseId = list(Nurse.objects.all().values())[0]["empNo"]
    nurseList = list(Nurse.objects.all().values())
    return render(request, 'nurseAreaAdjust.html', {
        "nurseId": nurseId,
        'nurseList': nurseList
    })

def NurseList(request):
    if request.method == "GET":
        nurseList = list(Nurse.objects.all().values())
        return render(request, 'nurseAreaNurseList.html', {
            'nurseList': nurseList
        })
    else:
        empNo = request.POST.get("empNo")
        n_name = request.POST.get("nurseName")
        Nurse.objects.create(
            empNo=empNo,
            n_name=n_name
        )
        return JsonResponse({'status': 'success'})
    
def DeleteNurse(request):
    empNo = request.POST.get("empNo")
    Nurse.objects.filter(empNo=empNo).delete()
    return JsonResponse({'status': 'success'})

# 取得資料
def get_record(request, shift):
    nurseList = list(Nurse.objects.all().values())
    if request.method == 'POST':
        idh_list = request.POST.get('idh-patients-list')
        update_idh = idh_list.split('-')[0:-1]
        t, shift, patients = get_update_idh_patients(shift, update_idh)
        form = False
        print("update_idh:", update_idh)
        print("idh_bed:", patients["idh_bed"])
    else:
        t, shift, patients = get_idh_patients(shift)
        form = True
    return render(request, 'feedback.html', {
        "form": form,
        "t": t,
        "shift": shift,
        "a_patients": patients["a_patients"],
        "b_patients": patients["b_patients"],
        "left_patients": patients["left_patients"],
        "bottom_patients": patients["bottom_patients"],
        "idh_patients": patients["idh_patients"],
        "idh_bed": patients["idh_bed"],
        "nurseList": nurseList
    })

# 加上ebm預測 (含狀態回填修正與 Debug)
def get_patients():
    time = get_time()
    # 取得當前正在透析的紀錄

    now_dialysis = Dialysis.objects.filter(start_time__lte=time, end_time__gte=time)
    
    a_patients = []
    b_patients = []
    left_patients = []
    bottom_patients = []
    
    # 預測邏輯初始化
    if len(now_dialysis) <= 1:
        all_idh = [0]
        all_idh_previous = [0]
        do_pred = False
    else:
        # 取得該診次病人的最新預測紀錄
        preds = Predict.objects.filter(d_id=now_dialysis[0].d_id).order_by('pred_time').reverse()
        last_pred = datetime.min if len(preds) == 0 else preds[0].pred_time
        
        # 判定是否需要執行每小時一次的大規模預測 (舊模型)
        if datetime.now() >= last_pred + timedelta(minutes=60):
            do_pred = True
            try:
                # 這裡調用您原本的預測模型
                all_idh = predict_idh() 
            except:
                all_idh = [0] * 32
            
            if len(preds) > 0:
                same_preds = Predict.objects.filter(
                    pred_time__date=preds[0].pred_time.date(), 
                    pred_time__hour=preds[0].pred_time.hour
                ).order_by('flag')
                all_pred_idh = [s.pred_idh for s in same_preds]
                all_idh_previous = [np.float32(a) for a in all_pred_idh] if all_pred_idh else [0]
            else:
                all_idh_previous = [0]
        else:
            do_pred = False
            if len(preds) > 0:
                same_preds = Predict.objects.filter(
                    pred_time__date=preds[0].pred_time.date(), 
                    pred_time__hour=preds[0].pred_time.hour
                ).order_by('flag')
                all_pred_idh = [s.pred_idh for s in same_preds]
                all_idh = [np.float32(a) for a in all_pred_idh] if all_pred_idh else [0]
                all_idh_previous = [np.float32(a) for a in all_pred_idh] if all_pred_idh else [0]
            else:
                all_idh = [0]
                all_idh_previous = [0]
    
    flag = 0
    # 對應您系統的四個區域
    all_area = [a_area, b_area, left_area, bottom_area]
    all_patients = [a_patients, b_patients, left_patients, bottom_patients]
    
    for a in range(len(all_area)):
        for index, bed in enumerate(all_area[a]):
            patient = {'bed': bed, 'idh': 0}
            for d in now_dialysis:
                if bed == d.bed:
                    start_time = d.start_time
                    
                    # === 加密解密保留區 ===
                    try:
                        p_obj = Patient.objects.filter(p_id=d.p_id.p_id)[0]
                        # 解密 ID 和 姓名供前端顯示
                        p_obj.display_id = CryptoManager.decrypt_deterministic(p_obj.p_id)
                        p_obj.display_name = CryptoManager.decrypt_deterministic(p_obj.p_name)
                        patient['id'] = p_obj
                        print(patient['id'])
                    except IndexError:
                        patient['id'] = '---'
                        continue
                    # =====================
                    
                    patient['setting'] = d
                    r = Record.objects.filter(d_id=d.d_id, record_time__gte=start_time, record_time__lte=time).order_by('record_time')
                    
                    if len(r) == 0:
                        patient['id'] = '---'
                        continue
                    else:
                        patient['record'] = r.last()
                    
                    # 計算舊模型 IDH 機率
                    if flag < len(all_idh) and flag < len(all_idh_previous):
                        if time.minute == 30:
                            patient['idh'] = int(round(all_idh[flag] * 100))
                        else:
                            patient['idh'] = max(
                                int(all_idh_previous[flag] * 100),
                                int(round(all_idh[flag] * 100))
                            )
                    else:
                        patient['idh'] = 0
                    
                    patient['random_code'] = d.random_code

                    # ========== [核心修正] EBM 預測區塊 (含 Debug) 這邊需要改 ==========
                    first_record = Record.objects.filter(d_id=d.d_id).order_by('record_time').last()
                    ebm_warning = False  
                    ebm_prob = 0.0
                    
                    if first_record:
                        time_since_first_record = (datetime.now() - first_record.record_time).total_seconds()
                        # print("1",time_since_first_record)

                        interval_index = float(time_since_first_record % 1800)
                        # print(interval_index)
                        
                        # 為了不跟舊模型的 flag 衝突，EBM 的 flag 設為負數且隨區間遞減 (-1, -2, -3...)
                        current_ebm_flag = -1 - interval_index

                        # 檢查「當前這個 30 分鐘區間」是否已經做過 EBM 預測
                        existing_ebm_pred = Predict.objects.filter(d_id=d.d_id, flag=current_ebm_flag).first()
                        # print(existing_ebm_pred)
                            
                        if not existing_ebm_pred:
                            # === Case A: 尚未預測過，執行預測 ===
                            print(f"[EBM NEW] Bed {bed} 符合條件，開始預測...")
                            try:
                                from interface.model.EBM import predict_idh_ebm
                                ebm_prob = predict_idh_ebm(d.d_id, use_database_flag=False)
                                
                                # 門檻判定
                                if ebm_prob >= 0.01 and d.random_code == 1:
                                    ebm_warning = True
                                    print(f"[EBM ALERT] Bed {bed} 觸發警告! 機率: {ebm_prob}")
                                    # === [新增] 自動觸發「待確認」狀態 ===
                                    # 檢查目前該床位是否已  經有「尚未處理」的警告，避免重複建立
                                    has_unhandled_warning = Warnings.objects.filter(p_bed=bed, dismiss_time__isnull=True).exists()
                                    
                                    if not has_unhandled_warning:
                                        # 取得病患真實姓名 (前面已經透過 CryptoManager 解密存在 p_obj.display_name 中)
                                        real_name = getattr(p_obj, 'display_name', '系統預測')
                                        
                                        # 建立一筆警告紀錄，因為沒有給 dismiss_time，前端就會亮起「待確認」的 icon！
                                        Warnings.objects.create(
                                            p_bed=bed,
                                            p_name=real_name,
                                            click_time=datetime.now()
                                        )
                                    # =====================================
                                else:
                                    print("not alert")

                                # 儲存結果
                                Predict.objects.create(
                                    d_id=d, 
                                    flag=current_ebm_flag,  # ✅ 換成我們算出來的動態 flag 
                                    pred_idh=Decimal(str(ebm_prob))
                                )
                            except Exception as e:
                                print(f"[EBM ERROR] Bed {bed} 預測失敗: {e}")
                        else:
                            # === Case B: 已經預測過，從資料庫撈回數值 ===
                            try:
                                # 將 Decimal 轉回 float
                                ebm_prob = float(existing_ebm_pred.pred_idh)
                                
                                # [關鍵修正] 重新判定警告狀態 (確保前端刷新的時候狀態正確)
                                if ebm_prob >= 0.01 and d.random_code == 1:
                                    ebm_warning = True
                                
                                # [DEBUG 2] 確認有讀取到歷史資料
                                # print(f"[EBM LOAD] Bed {bed} 使用歷史資料: {ebm_prob*100:.1f}% (Warning: {ebm_warning})")

                            except Exception as e:
                                print(f"[EBM READ ERROR] Bed {bed}: {e}")
                        # print(f"[EBM SKIP] Bed {bed} 超過 30 分鐘")

                    # 傳遞到前端
                    patient['ebm_warning'] = ebm_warning
                    patient['ebm_prob'] = int(round(ebm_prob * 100))
                    # =================================================

                    # === 版本核心：警告與處置邏輯 ===
                    # 1. 判定是否已點擊警示 (First Click)
                    w_clicks = Warnings.objects.filter(p_bed=bed).order_by('click_time').reverse()
                    if len(w_clicks) == 0:
                        patient['first_click'] = False 
                    else:
                        last_half_hour = time.replace(minute=30, second=0, microsecond=0)
                        if time.minute < 30:
                            last_half_hour -= timedelta(hours=1)
                        patient['first_click'] = w_clicks[0].click_time >= last_half_hour
                    
                    # 2. 判定是否已完成處置回饋 (Done Warning)
                    w_dismissals = Warnings.objects.filter(p_bed=bed).order_by('dismiss_time').reverse()
                    should_be_false = False
                    if len(w_dismissals) == 0 or w_dismissals[0].dismiss_time == None:
                        should_be_false = True
                    else:
                        last_half_hour = time.replace(minute=30, second=0, microsecond=0)
                        if time.minute < 30:
                            last_half_hour -= timedelta(hours=1)
                        should_be_false = w_dismissals[0].dismiss_time < last_half_hour

                    # 特殊時間窗口判定
                    if should_be_false and 30 <= time.minute <= 35:
                        patient['done_warning'] = False
                    elif not should_be_false:
                        patient['done_warning'] = True
                    # =================================================
        
                    # 儲存舊模型預測值
                    if do_pred and flag < len(all_idh):
                        pred_obj = Predict(d_id=d, flag=flag, pred_idh=Decimal(str(all_idh[flag])))
                        pred_obj.save()
                    
                    if flag == 32: continue
                    flag += 1
                    continue
            
            if 'id' not in patient:
                patient['id'] = '---'
            all_patients[a].append(patient)
    
    # 高風險清單獲取 (保留您系統原有的函式)
    try:
        high_risk_patients = get_high_risk_patients(time)
    except:
        high_risk_patients = []
    
    return {
        'a_patients': a_patients, 
        'b_patients': b_patients, 
        'left_patients': left_patients,
        'bottom_patients': bottom_patients,
        'high_risk_patients': high_risk_patients,
    }

# 115/02/06 update for EBM high risk patient fetching
def get_high_risk_patients(current_time):
    """
    獲取高風險病患清單 (移除校準邏輯，改用 EBM 原始分數)
    """
    high_risk_list = []
    
    # [關鍵修改] 移除原本加載 iso_calibration.joblib 的代碼

    try:
        now_dialysis = Dialysis.objects.filter(
            start_time__lte=current_time, 
            end_time__gte=current_time,
            random_code=1
        )
        
        for dialysis in now_dialysis:
            try:
                # 取得該床位最新的預測紀錄
                latest_predict = Predict.objects.filter(
                    d_id=dialysis.d_id
                ).order_by('-pred_time').first()
                
                if latest_predict:
                    # [關鍵修改] 直接使用 Predict 表中的原始機率值 (EBM 分數)
                    final_prob = float(latest_predict.pred_idh)

                    # 設定篩選門檻 (例如 1% 以上列入清單)
                    FILTER_THRESHOLD = 0.85
                    
                    if final_prob >= FILTER_THRESHOLD:
                        patient = Patient.objects.filter(p_id=dialysis.p_id.p_id).first()
                        latest_record = Record.objects.filter(
                            d_id=dialysis.d_id,
                            record_time__lte=current_time
                        ).order_by('-record_time').first()
                        
                        # 檢查處置狀態
                        latest_warning = Warnings.objects.filter(
                            p_bed=dialysis.bed,
                            dismiss_time__isnull=False
                        ).order_by('-dismiss_time').first()
                        is_treated = True if latest_warning else False
                        
                        # [關鍵修改] 解密病患姓名供前端顯示
                        real_name = CryptoManager.decrypt_deterministic(patient.p_name)
                        
                        if patient and latest_record:
                            risk_percentage = int(final_prob * 100)
                            
                            # 風險分級邏輯 (可依 EBM 特性調整)
                            if risk_percentage >= 85: # 參考 RyanJ 警告門檻
                                risk_level = 'high'
                            elif risk_percentage >= 50:
                                risk_level = 'medium'
                            else:
                                risk_level = 'low'

                            high_risk_list.append({
                                'bed': dialysis.bed,
                                'patient_name': real_name,
                                'risk_percentage': risk_percentage,
                                'risk_level': risk_level,
                                'sbp': latest_record.SBP,
                                'dbp': latest_record.DBP,
                                'is_treated': is_treated,
                                # [新增] 這一行是關鍵！補上預測時間
                                'pred_time': latest_predict.pred_time,
                            })

            except Exception as e:
                print(f"處理高風險病患 {dialysis.bed} 出錯: {e}")
                continue
        
        # 依照機率排序
        high_risk_list.sort(key=lambda x: x['risk_percentage'], reverse=True)
        
    except Exception as e:
        print(f"獲取高風險清單失敗: {e}")
        
    return high_risk_list

def get_detail(request, area, bed, idh):
    time = get_time()
    patient = {}
    
    # 取得透析資訊
    d_queryset = Dialysis.objects.filter(bed=bed, start_time__lte=time, end_time__gte=time)
    if not d_queryset.exists():
        print(f"No dialysis record found for bed {bed}")
        return redirect('index', area=area)

    d = d_queryset[0]
    print("bed:", bed, "d:", d)
    start_time = d.start_time
    
    # patient data & 解密
    patient_obj = Patient.objects.filter(p_id=d.p_id.p_id)[0]
    patient_obj.display_id = CryptoManager.decrypt_deterministic(patient_obj.p_id)
    patient_obj.display_name = CryptoManager.decrypt_deterministic(patient_obj.p_name)
    
    patient['id'] = patient_obj
    patient['setting'] = d
    
    # latest dialysis record
    r_today = Record.objects.filter(d_id=d.d_id, record_time__gte=start_time, record_time__lte=time).order_by('record_time')
    patient['record'] = r_today.last() if r_today.exists() else None

    # all record
    all_dialysis = Dialysis.objects.filter(p_id=d.p_id.p_id, times__gte=d.times-2)
    temp = []
    for dialysis in all_dialysis:
        record_list = Record.objects.filter(d_id=dialysis.d_id, record_time__lte=time).select_related().order_by('record_time')
        for record in record_list:
            if record.d_id.temperature <= 0: record.d_id.temperature = '-'
            if record.d_id.start_temperature <= 0: record.d_id.start_temperature = '-'
            if record.d_id.ESA == str(-1): record.d_id.ESA = '-'
            if record.flush == -1.000: record.flush = '-'
            if record.record_time > (datetime.now() - timedelta(minutes=10)): record.in10minutes = True
            temp.append(record)

    patient['all_record'] = temp
    diff = {}
    
    # weight diff logic
    if d.ideal_weight > 0:
        diff_weight = round(d.before_weight - d.ideal_weight, 1)
        diff_percentage = round(diff_weight / d.ideal_weight * 100, 1)
        if diff_weight > 0:
            diff['value'] = '+' + str(diff_weight)
            diff['percentage'] = '+' + str(diff_percentage) + "%"
            diff['per_width'] = diff_percentage * 10
            diff['class'] = 'diff-pos'
        else:
            diff['value'] = str(diff_weight)
            diff['percentage'] = str(diff_percentage) + "%"
            diff['per_width'] = (-1) * diff_percentage * 10
            diff['class'] = 'diff-neg'
    
    patients = get_patients()

    # plot 
    plot_data = []
    if r_today:
        for r in r_today:
            timestamp = str(r.record_time.strftime("%Y-%m-%d %H:%M"))
            plot_data.append({
                "timestamp": timestamp,
                "SBP": float(r.SBP),
                "pulse": r.pulse,
                "CVP": r.CVP, 
            })
            
        time_string = timestamp
        for i in range(8):
            timestamp_obj = datetime.strptime(time_string, "%Y-%m-%d %H:%M") + timedelta(hours=1)
            time_string = str(timestamp_obj.strftime("%Y-%m-%d %H:%M"))
            if timestamp_obj < d.start_time + timedelta(hours=4):
                if len(plot_data) < 8:
                    plot_data.append({
                        "timestamp": time_string,
                        "SBP": None,
                        "pulse": None,
                        "CVP": None,
                    })
            else:
                break
    
    # === 🔥 115/01/27[關鍵修改] 傳入 idh 機率參數，生成 PDF 格式總結 ===
    # 這裡將 idh (預測機率值) 傳入函式中
    llm_summary_text = get_llm_summary(bed, patient_obj.p_id, idh_prob=idh)
    # ========================================================

    return render(request, 'index.html', {
        "home": False,
        "area": area,
        "a_patients": patients["a_patients"],
        "b_patients": patients["b_patients"],
        "left_patients": patients["left_patients"],    
        "bottom_patients": patients["bottom_patients"],
        "high_risk_patients": patients.get("high_risk_patients", []),
        "id": patient['id'],
        "setting": patient['setting'],
        "record": patient['record'],
        "idh": idh,
        "diff": diff,
        "all_record": patient['all_record'],
        "chart": json.dumps(plot_data),
        "llm_summary": llm_summary_text, 
    })

def get_idh_patients(shift):
    time =get_time()
    t = shift
    if shift == 0:
        shift = "早"
        shift_start = time.replace(hour=10, minute=0)
        shift_end = time.replace(hour=11, minute=0)
    elif shift == 1:
        shift = "午"
        shift_start = time.replace(hour=15, minute=0)
        shift_end = time.replace(hour=16, minute=0)
    else:
        shift = "晚"
        shift_start = time.replace(hour=20, minute=0)
        shift_end = time.replace(hour=21, minute=0)
    now_dialysis = Dialysis.objects.filter(start_time__lte=shift_start, end_time__gte=shift_end)
    a_patients, b_patients, left_patients, bottom_patients = [], [], [], []
    idh_patients = []
    idh_bed = ''
    all_area = [a_area, b_area, left_area, bottom_area]
    all_patients = [a_patients, b_patients, left_patients, bottom_patients]
    for a in range(len(all_area)):
        for index, bed in enumerate(all_area[a]):
            patient = {}
            patient = {'bed': bed}
            for d in now_dialysis:
                if bed == d.bed:
                    start_time = d.start_time
                    patient['id'] = Patient.objects.filter(p_id=d.p_id.p_id)[0]
                    patient['setting'] = d
                    records = Record.objects.filter(d_id=d.d_id, record_time__gte=start_time, record_time__lte=d.end_time).order_by('record_time')
                    if len(records) == 0:
                        continue
                    patient['record'] = records[len(records) - 1]
                    patient['status'] = 0
                    plot_data = []
                    for r in range(len(records)):
                        if records[r].SBP <= 90 and records[r].SBP != 0:
                            patient['status'] = 1
                            for r in range(len(records)):
                                if r > 1 and records[r].SBP < records[r-1].SBP - 20 and records[r].SBP != 0:
                                    patient['status'] = 3
                                    break
                        elif r > 1 and records[r].SBP < records[r-1].SBP - 20 and records[r].SBP != 0:
                            patient['status'] = 2
                    if patient['status'] != 0:
                        idh_patients.append(patient)
                        idh_bed += bed + '-'
                    for re in records:
                        timestamp = str(re.record_time.strftime("%Y-%m-%d %H:%M"))
                        sbp = float(re.SBP)
                        pulse = re.pulse
                        cvp = re.CVP
                        plot_data.append({
                            "timestamp": timestamp,
                            "SBP": sbp,
                            "pulse": pulse,
                            "CVP": cvp, 
                        })
                    patient['chart_id'] = "linechart-" + str(bed)
                    patient['chart'] = json.dumps(plot_data)
            if 'id' not in patient:
                patient['id'] = '---' 
            all_patients[a].append(patient)
    return t, shift, {
        'a_patients': a_patients, 
        'b_patients': b_patients, 
        'left_patients': left_patients,
        'bottom_patients': bottom_patients,
        'idh_patients': idh_patients,
        'idh_bed': idh_bed,
    }

def get_update_idh_patients(shift, update_idh):
    time = get_time()
    t = shift
    if shift == 0:
        shift = "早"
        shift_start = time.replace(hour=10, minute=0)
        shift_end = time.replace(hour=12, minute=0)
    elif shift == 1:
        shift = "午"
        shift_start = time.replace(hour=14, minute=0)
        shift_end = time.replace(hour=16, minute=0)
    else:
        shift = "晚"
        shift_start = time.replace(hour=19, minute=0)
        shift_end = time.replace(hour=21, minute=0)
    now_dialysis = Dialysis.objects.filter(start_time__lte=shift_start, end_time__gte=shift_end)
    a_patients, b_patients, left_patients, bottom_patients = [], [], [], []
    idh_patients = []
    idh_bed = ''
    all_area = [a_area, b_area, left_area, bottom_area]
    all_patients = [a_patients, b_patients, left_patients, bottom_patients]
    for a in range(len(all_area)):
        for index, bed in enumerate(all_area[a]):
            patient = {}
            patient = {'bed': bed}
            for d in now_dialysis:
                if bed == d.bed:
                    start_time = d.start_time
                    patient['id'] = Patient.objects.filter(p_id=d.p_id.p_id)[0]
                    patient['setting'] = d
                    records = Record.objects.filter(d_id=d.d_id, record_time__gte=start_time, record_time__lte=d.end_time).order_by('record_time')
                    
                    # === [修正開始] 加入此判斷：如果沒有紀錄就跳過 ===
                    if len(records) == 0:
                        continue
                    # === [修正結束] ===
                    
                    patient['record'] = records[len(records) - 1]
                    patient['status'] = 0
                    plot_data = []
                    for r in range(len(records)):
                        if records[r].SBP <= 90 and records[r].SBP != 0:
                            patient['status'] = 1
                            if bed not in idh_bed: idh_bed += bed + '-'
                            for r in range(len(records)):
                                if r > 1 and records[r].SBP < records[r-1].SBP - 20 and records[r].SBP != 0:
                                    patient['status'] = 3
                                    if bed not in idh_bed: idh_bed += bed + '-'
                                    break
                        elif r > 1 and records[r].SBP < records[r-1].SBP - 20 and records[r].SBP != 0:
                            patient['status'] = 2
                            if bed not in idh_bed: idh_bed += bed + '-'
                    if bed in update_idh:
                        idh_patients.append(patient)
                        
                    for re in records:
                        timestamp = str(re.record_time.strftime("%Y-%m-%d %H:%M"))
                        sbp = float(re.SBP)
                        pulse = re.pulse
                        cvp = re.CVP
                        plot_data.append({
                            "timestamp": timestamp,
                            "SBP": sbp,
                            "pulse": pulse,
                            "CVP": cvp, 
                        })
                    patient['chart_id'] = "linechart-" + str(bed)
                    patient['chart'] = json.dumps(plot_data)
            if 'id' not in patient:
                patient['id'] = '---'
            all_patients[a].append(patient)  
    return t, shift, {
        'a_patients': a_patients, 
        'b_patients': b_patients, 
        'left_patients': left_patients,
        'bottom_patients': bottom_patients,
        'idh_patients': idh_patients,
        'idh_bed': idh_bed,
    }

# 回饋表單
def post_feedback(request):
    time = get_time()
    if request.method == 'POST':
        try:
            idh_time = []
            p_id = request.POST.getlist('patient')
            for id in p_id:
                idh_time.append(request.POST.getlist('idh-time-' + id))
            setting = request.POST.getlist('setting')

            target_bed = None # 用來記住床號

            if len(request.POST.getlist("bands")) > 0:
                bands = request.POST.getlist("bands")[0].split(',')
                empNo = request.POST.getlist("nurseId")[0]
                for index, id in enumerate(p_id):
                    dialysis = Dialysis.objects.get(d_id=setting[index])
                    
                    target_bed = dialysis.bed # 抓取床號

                    f = Feedback(d_id=dialysis, idh_time=idh_time[index], empNo=empNo) 
                    f.save()
                
                # ... (中間 bands 的邏輯保持不變) ...
                for idh in bands:
                    if idh != '':
                        patient = idh.split('-')[0]
                        record = idh.split('-')[2]
                        d = Dialysis.objects.filter(p_id=patient, start_time__lt=time)
                        if d.exists():
                            r = Record.objects.filter(d_id=d[d.count()-1])[int(record)]
                            f_record = Record.objects.get(r_id=r.r_id)
                            f_record.is_idh = True
                            f_record.save()

            print("Successfully fill in the feedback form")
            
            # [關鍵修改] 改回傳 JSON，前端 JS 收到後會自己用相對路徑跳轉，不會被導去 127.0.0.1
            return JsonResponse({'status': 'success', 'bed_code': target_bed})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'status': 'error', 'msg': str(e)})

    return JsonResponse({'status': 'error', 'msg': 'Invalid method'})

# 警示表單
def warning_click(request):
    print("Warning click")
    click_time = datetime.now() # 點掉閃爍
    if request.method == 'POST':
        pBed = request.POST.get('patientBed')
        pName = request.POST.get('patientName')
        empNo = request.POST.get('empNo')
    try:
        w = Warnings(click_time=click_time, empNo=empNo, p_bed=pBed, p_name=pName)
        w.save()
        return JsonResponse({"status": 'success'})
    except Exception as error:
        return JsonResponse({"status": 'fail', "msg": str(error)})

def warning_feedback(request):
    if request.method == 'POST':
        dismiss_time = datetime.now() # 0312 紀錄血壓
        pBed = request.POST.get('patientBed')
        pName = request.POST.get('patientName')
        empNo = request.POST.get('empNo')
        warning_SBP = request.POST.get('SBP')
        warning_DBP = request.POST.get('DBP')
        
        # 症狀
        is_sign = True if request.POST.get('sign-') == '1' else False
        # 口服藥物
        drug_midodrine = request.POST.get('drug-midodrine')
        drug_other = request.POST.get('drug-other-check')
        drug_all = [i for i in [drug_midodrine, drug_other] if i is not None]
        is_drug = True if len(drug_all) > 0 else False
        # 針劑藥物
        inject_IV_Glucose = request.POST.get('drug-IV_Glucose')
        inject_other = request.POST.get('inject-other-check')
        inject_all = [i for i in [inject_IV_Glucose, inject_other] if i is not None]
        is_inject = True if len(inject_all) > 0 else False
        # 調整透析設定
        setting_low_blood_flow = request.POST.get('setting-low_blood_flow')
        setting_low_UF = request.POST.get('setting-low_UF')
        setting_low_dialysate_flow = request.POST.get('setting-low_dialysate_flow')
        setting_other = request.POST.get('setting-other-check')
        setting_all = [i for i in [setting_low_blood_flow, setting_low_UF, setting_low_dialysate_flow, setting_other] if i is not None]
        is_setting = True if len(setting_all) > 0 else False
        # 護理處置
        nursing_HLFH = request.POST.get('nursing-HLFH')
        nursing_low_temp = request.POST.get('nursing-low_temp')
        nursing_flush = request.POST.get('nursing-flush')
        nursing_other = request.POST.get('nursing-other-check')
        nursing_all = [i for i in [nursing_HLFH, nursing_low_temp, nursing_flush, nursing_other] if i is not None]
        is_nursing = True if len(nursing_all) > 0 else False
        # 其他處理
        other_observe = request.POST.get('other-observe')
        other_other = request.POST.get('other-other-check')
        other_all = [i for i in [other_observe, other_other] if i is not None]
        is_other = True if len(other_all) > 0 else False
        # 護理師處置時間
        handle_time = request.POST.get('handle-time')
        
        print("HANDLE TIME:",handle_time)
        print("DRUG:", drug_all, is_drug)
        print("INJECT:", inject_all, is_inject)
        print("SETTING:", setting_all, is_setting)
        print("NURSING:", nursing_all, is_nursing)
        print("OTHER:", other_all, is_other)
        print(f'Dismiss: {dismiss_time} empNo: {empNo}, SBP: {warning_SBP}, DBP: {warning_DBP}, patientBed: {pBed}, patientName: {pName}')
        ws = Warnings.objects.filter(p_bed=pBed, p_name=pName)
        try:
            if len(ws) > 1:
                ws.order_by('-click_time')[0].update(empNo=empNo, 
                                                     warning_SBP=warning_SBP, 
                                                     warning_DBP=warning_DBP, 
                                                     dismiss_time=dismiss_time,
                                                     is_sign=is_sign, 
                                                     is_drug=is_drug, 
                                                     is_inject=is_inject, 
                                                     is_setting=is_setting, 
                                                     is_nursing=is_nursing, 
                                                     is_other=is_other, 
                                                     drug_all=drug_all,
                                                     inject_all=inject_all,
                                                     setting_all=setting_all,
                                                     nursing_all=nursing_all,
                                                     other_all=other_all,
                                                     handle_time=handle_time)
            elif len(ws) == 1:
                ws.update(empNo=empNo, 
                          warning_SBP=warning_SBP, 
                          warning_DBP=warning_DBP, 
                          dismiss_time=dismiss_time,
                          is_sign=is_sign, 
                          is_drug=is_drug, 
                          is_inject=is_inject, 
                          is_setting=is_setting, 
                          is_nursing=is_nursing, 
                          is_other=is_other, 
                          drug_all=drug_all,
                          inject_all=inject_all,
                          setting_all=setting_all,
                          nursing_all=nursing_all,
                          other_all=other_all,
                          handle_time=handle_time)
            else:
                w = Warnings(empNo=empNo, 
                             p_bed=pBed, 
                             p_name=pName, 
                             warning_SBP=warning_SBP, 
                             warning_DBP=warning_DBP, 
                             click_time=dismiss_time, 
                             dismiss_time=dismiss_time,
                             is_sign=is_sign, 
                             is_drug=is_drug, 
                             is_inject=is_inject, 
                             is_setting=is_setting, 
                             is_nursing=is_nursing, 
                             is_other=is_other, 
                             drug_all=drug_all,
                             inject_all=inject_all,
                             setting_all=setting_all,
                             nursing_all=nursing_all,
                             other_all=other_all,
                             handle_time=handle_time)
                w.save()
            print("Success update warning")
            return JsonResponse({
                "status": 'success',
                "bed": pBed,
                "treated": True,
                "timestamp": dismiss_time.isoformat()
            })
        except Exception as error:
            return JsonResponse({"status": 'fail', "msg": str(error)})

# 護理師專區
def get_nurse_patients(bed_list):
    patients = get_patients()
    nurse_patients = []
    for index, bed in enumerate(bed_list):
        for p_area in patients.keys():
            for p in patients[p_area]:
                if p['bed'] == bed:
                    nurse_patients.append(p)
    return {'nurse_patients': nurse_patients}

def get_nurse_detail(request, nurseId, bed, idh):
    time = get_time()
    patient = {}
    d = Dialysis.objects.filter(bed=bed, start_time__lte=time, end_time__gte=time)[0]
    start_time = d.start_time
    # patient data
    patient['id'] = Patient.objects.filter(p_id=d.p_id.p_id)[0]
    # latest dialysis information
    patient['setting'] = d
    # latest dialysis record
    r_today = Record.objects.filter(d_id=d.d_id, record_time__gte=start_time, record_time__lte=time).order_by('record_time')
    patient['record'] = r_today[len(r_today) - 1]

    # all record
    all_dialysis = Dialysis.objects.filter(p_id=d.p_id.p_id, times__gte=d.times-2)
    temp = []
    for dialysis in all_dialysis:
        record_list = Record.objects.filter(d_id=dialysis.d_id, record_time__lte=time).select_related().order_by('record_time')
        for record in record_list:
            if record.d_id.temperature <= 0: record.d_id.temperature = '-'
            if record.d_id.start_temperature <= 0: record.d_id.start_temperature = '-'
            if record.d_id.ESA == str(-1): record.d_id.ESA = '-'
            if record.flush == -1.000: record.flush = '-'
            temp.append(record)

    patient['all_record'] = temp
    diff = {}
    # weight
    if d.ideal_weight > 0:
        diff_weight = round(d.before_weight - d.ideal_weight, 1)
        diff_percentage = round(diff_weight / d.ideal_weight * 100, 1)
        if diff_weight > 0:
            diff['value'] = '+' + str(diff_weight)
            diff['percentage'] = '+' + str(diff_percentage) + "%"
            diff['per_width'] = diff_percentage * 10
            diff['class'] = 'diff-pos'
        else:
            diff['value'] = str(diff_weight)
            diff['percentage'] = str(diff_percentage) + "%"
            diff['per_width'] = (-1) * diff_percentage * 10
            diff['class'] = 'diff-neg'
    patients = get_nurse_patients([bed])
    
    # plot 
    plot_data = []
    for r in r_today:
        timestamp = str(r.record_time.strftime("%Y-%m-%d %H:%M"))
        sbp = float(r.SBP)
        pulse = r.pulse
        cvp = r.CVP
        plot_data.append({
            "timestamp": timestamp,
            "SBP": sbp,
            "pulse": pulse,
            "CVP": cvp, 
        })
    time_string = timestamp
    for i in range(8):
        timestamp = datetime.strptime(time_string, "%Y-%m-%d %H:%M") + timedelta(hours=1)
        time_string = str(timestamp.strftime("%Y-%m-%d %H:%M"))
        if timestamp < d.start_time + timedelta(hours=4):
            if len(plot_data) < 8:
                plot_data.append({
                    "timestamp": time_string,
                    "SBP": None,
                    "pulse": None,
                    "CVP": None,
                })
        else:
            break

    return render(request, 'nurseAreaSearch.html', {
        "nurseId": nurseId,
        "home": False,
        "nurse_patients": patients["nurse_patients"], #1226
        "id": patient['id'],
        "setting": patient['setting'],
        "record": patient['record'],
        "idh": idh,
        "diff": diff,
        "all_record": patient['all_record'],
        "chart": json.dumps(plot_data),
    })

# 輸出報表
def export_file(request):
    '''0109 Export patient data to Excel file'''
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    if start_time != '' and end_time != '':
        print("start time:", start_time, ", end time: ", end_time)
        start_time = datetime.strptime(str(start_time), "%Y-%m-%dT%H:%M")
        end_time = datetime.strptime(str(end_time), "%Y-%m-%dT%H:%M")
        # Create the export view 
        filename = 'PatientData.xlsx'
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        wb = Workbook()
        ws = wb.active
        ws.title = "all_record"
        ws.append(["員工號", "姓名", "床位", "警示關閉時間", "SBP", "DBP", "填寫時間",
                   "口服藥物", "針劑藥物", "調整透析設定", "護理處置", "其他處理"])
        warnings = Warnings.objects.filter(dismiss_time__gte=start_time, dismiss_time__lte=end_time)
        if len(warnings) != 0:
            for warning in warnings:
                data = [warning.empNo, warning.p_name, warning.p_bed, warning.click_time, warning.warning_SBP, warning.warning_DBP, warning.dismiss_time,
                        warning.drug_all, warning.inject_all, warning.setting_all, warning.nursing_all, warning.other_all,warning.handle_time]
                ws.append(data)
        # Save the workbook to the HttpResponse
        wb.save(response)
        print("Success exporting file", response)
        return response
    else:
        return HttpResponse("請提供有效的起始時間和結束時間")
    
# def sync_csv_to_db():
#     """
#     讀取 CSV 並同步到資料庫 (Patient, Dialysis, Nurse_Record)
#     包含：資料加密 (ID & 姓名)、防重複機制
#     """
#     csv_path = os.path.join(settings.BASE_DIR, 'interface', 'data', 'patient_data.csv')
    
#     if not os.path.exists(csv_path):
#         print(f"⚠️ [Sync] 找不到 CSV 檔案: {csv_path}")
#         return

#     try:
#         with open(csv_path, 'r', encoding='utf-8-sig') as f:
#             reader = csv.DictReader(f)
#             count_new = 0
#             count_update = 0
            
#             for row in reader:
#                 try:
#                     # --- 1. 準備資料 ---
#                     raw_id_str = row.get('case_number', '').strip()
#                     raw_name = row.get('name', '').strip()
                    
#                     if not raw_id_str: continue

#                     # [加密] ID 與 姓名 (決定性加密)
#                     enc_id = CryptoManager.encrypt_deterministic(raw_id_str)
#                     enc_name = CryptoManager.encrypt_deterministic(raw_name)

#                     # --- 2. 同步 Patient (基本資料) ---
#                     # 解析生日
#                     try:
#                         birth_str = row.get('birthday', '')
#                         if birth_str:
#                             birth_date = datetime.strptime(birth_str, '%Y-%m-%d').date()
#                         else:
#                             birth_date = datetime.strptime('2000-01-01', '%Y-%m-%d').date()
#                     except:
#                         birth_date = datetime.strptime('2000-01-01', '%Y-%m-%d').date()

#                     # 使用加密後的 ID (enc_id) 當主鍵
#                     patient, _ = Patient.objects.update_or_create(
#                         p_id=enc_id,
#                         defaults={
#                             'p_name': enc_name, # 存加密姓名
#                             'gender': 'F',
#                             'birth': birth_date
#                         }
#                     )

#                     # --- 3. 同步 Dialysis (透析紀錄) ---
#                     dialysis_date = datetime.now()
#                     nurse_text = row.get('nurse_record', '')
#                     if nurse_text and len(nurse_text) > 10:
#                         try:
#                             dialysis_date = datetime.strptime(nurse_text[:10], '%Y-%m-%d')
#                         except:
#                             pass
                    
#                     dialysis, _ = Dialysis.objects.get_or_create(
#                         p_id=patient,
#                         start_time__date=dialysis_date.date(),
#                         defaults={
#                             'start_time': dialysis_date,
#                             'age': int(row.get('age', 0) or 0),
#                             'times': 1,
#                             'machine_id': 'Import',
#                             'bed': 'Import',
#                             'start_DBP': 0,
#                             'end_DBP': 0,
#                             'mode': 'HD',
#                             'machine': 'Fresenius',
#                             'channel': 'AvFistula',
#                             'heparin': 'General',
#                             'coagulation': 'None'
#                         }
#                     )

#                     # --- 4. 同步 Nurse_Record (完整資料) ---
#                     obj, created = Nurse_Record.objects.update_or_create(
#                         d_id=dialysis,
#                         defaults={
#                             'name': enc_name, # 存加密姓名
#                             'blood_type': row.get('blood_type'),
#                             'blood_rh': row.get('blood_rh'),
#                             'hbv': int(row.get('hbv', 0) or 0),
#                             'hcv': int(row.get('hcv', 0) or 0),
#                             'hiv': int(row.get('hiv', 0) or 0),
#                             'a_p': row.get('a+p'),
#                             'constraint': row.get('constraint'),
#                             'fall_risk': row.get('fall_risk'),
#                             'fiber_list': row.get('fiber_list'),
#                             'content': row.get('nurse_record'),
#                             'medical_order': row.get('order')
#                         }
#                     )
                    
#                     if created: count_new += 1
#                     else: count_update += 1

#                 except Exception as e:
#                     print(f"⚠️ [Sync] 處理單筆資料失敗: {e}")

#         print(f"✅ [Sync] CSV 同步完成: 新增 {count_new}, 更新 {count_update}")

#     except Exception as e:
#         print(f"❌ [Sync] 讀取 CSV 失敗: {e}")
    
@csrf_exempt
def update_treatment_status(request):
    """
    更新病患處置狀態 API
    """
    if request.method == 'POST':
        try:
            bed_name = request.POST.get('bedName')
            is_treated = request.POST.get('isTreated') == 'true'
            
            print(f"📝 收到處置狀態更新請求: 床位={bed_name}, 狀態={'已處置' if is_treated else '未處置'}")
            
            # 查找該床位的最新警示記錄
            warnings = Warnings.objects.filter(p_bed=bed_name).order_by('-click_time')
            
            if warnings.exists():
                latest_warning = warnings.first()
                
                if is_treated:
                    # 標記為已處置
                    latest_warning.dismiss_time = datetime.now()
                    latest_warning.save()
                    print(f"✅ 床位 {bed_name} 已標記為已處置")
                else:
                    # 取消已處置狀態
                    latest_warning.dismiss_time = None
                    latest_warning.save()
                    print(f"⚠️ 床位 {bed_name} 已取消處置狀態")
                
                return JsonResponse({
                    'status': 'success', 
                    'treated': is_treated,
                    'bed': bed_name
                })
            else:
                # 如果沒有警示記錄，創建一個新的
                w = Warnings(
                    p_bed=bed_name,
                    click_time=datetime.now(),
                    dismiss_time=datetime.now() if is_treated else None
                )
                w.save()
                print(f"🆕 為床位 {bed_name} 創建新的警示記錄")
                return JsonResponse({
                    'status': 'success', 
                    'treated': is_treated,
                    'bed': bed_name
                })
                
        except Exception as e:
            print(f"❌ 更新處置狀態失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method. Only POST is allowed.'
    }, status=400)


# 要改回
def corn_job():
    """修改後的 corn_job，加入錯誤處理"""
    try:
        fetchData()
        print("✅ Successfully fetch API")
    except Exception as e:
        print(f"⚠️ Fetch API 失敗: {e}")
        # 不中斷執行，繼續處理
    
    try:
        splitCSV()
        print("✅ Successfully split to 3 CSV files")
    except Exception as e:
        print(f"⚠️ Split CSV 失敗: {e}")
    
    try:
        saveData()
        print("✅ [corn_job]Successfully save new data to database")
    except Exception as e:
        print(f"⚠️ Save data 失敗: {e}")
        
    # try:
    #     sync_csv_to_db()
    # except Exception as e:
    #     print(f"⚠️ 自動同步 CSV 失敗: {e}")