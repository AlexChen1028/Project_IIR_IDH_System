import os
import datetime
import requests
import json
import pandas as pd

# 115/01/14 update: 引入加密模組
# 直接引入，如果失敗就讓它報錯，這樣才知道問題在哪
from interface.utils import CryptoManager

def getNowDate():
    now = datetime.datetime.now()
    year = '{:02d}'.format(now.year)
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    hour = '{:02d}'.format(now.hour)
    minute = '{:02d}'.format(now.minute)
    day_month_year = '{}-{}-{}'.format(year, month, day)
    # print('day_month_year: ' + day_month_year)
    return day_month_year

def getNowDatee():
    now = datetime.datetime.now()
    year = '{:02d}'.format(now.year)
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    hour = '{:02d}'.format(now.hour)
    minute = '{:02d}'.format(now.minute)
    day_month_year = '{}-{}-{} {}:{}'.format(year, month, day, hour, minute)
    # print('day_month_year: ' + day_month_year)
    return day_month_year

def getAPIResponse(day_month_year):
    url = os.environ.get('HOSPITAL_API_URL', 'http://localhost/php/dialysislist.php')
    param = {'date': day_month_year}

    ### API_Testing
    # url = 'https://jsonplaceholder.typicode.com/posts'
    # param = {}

    response = requests.get(url, params=param)
    response.raise_for_status()  # raises exception when not a 2xx response
    def get_now_date():
        """取得當前日期"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    """處理與保存資料"""
    if response.status_code == 200:
        try:
            # 去掉不必要的 meta 標籤，解析 JSON
            data = response.text.strip('<meta charset="UTF-8" />')
            data_list = json.loads(data)['data_list']

            # 動態生成檔案名稱，格式為 yyyy-mm.txt
            now = datetime.datetime.now()
            file_name = f"{now.year}-{now.month:02d}.txt"

            # 寫入文件
            with open(file_name, 'a') as file:
                file.write(f"Date: {get_now_date()}\n")
                file.write(data + "\n")
            
            print("Data saved successfully.")
        
        except Exception as error:
            data_list = []
            print("Error:", error)
    else:
        data_list = []
    return data_list

def convertCSV(data):
    col_name = ['ID', '姓名',	'性別',	'出生年月日',	'年齡',	'透析次數(本院)',	'透析開始時間',	'透析結束時間',	'紀錄時間',	'透析機編號',	'床位',	'體溫',	'開始體溫',	'透析前體重(kg)',	'理想體重(kg)',	'目標脫水量(L)',	'輸液量(L)',	'食物重量(kg)',	'預估脫水量(L)',	'設定脫水量(L)',	'結束體重(kg)',	'實際脫水量(L)',	'Start_SBP',	'Start_DBP',	'End_SBP',	'End_DBP',	'透析模式',	'透析器',	'開始透析液流速',	'開始血液流速',	'透析液Ca：3.0',	'傳導度：13.9',	'血管通路',	'Heparin',	'ESA',	'透析器凝血情況',	'血壓(收縮)',	'血壓(舒張)',	'脈搏',	'呼吸',	'血流速(ml/min)',	'透析液流速(ml/min)',	'靜脈壓(mmHg)',	'透析液壓(mmHg)',	'膜上壓(mmHg)',	'脫水速率',	'累積量',	'透析液溫度(℃)', '肝素注射量(ml/hr)',	'沖水量(L)',	'確認血管通路']
    res = pd.DataFrame.from_records(data, columns=col_name)
    res = res.sort_values(by=['ID', '透析開始時間', '透析結束時間', '紀錄時間'])
    row_indexes = res[res['床位'].apply(lambda x: x[0].isdigit())]
    res = res.drop(row_indexes.index)
    ### drop for patient with 2 IDs  ###
    row_indexes2 = res[res['ID'].apply(lambda x: x.isdigit()==False)]
    res = res.drop(row_indexes2.index)
    ####################################
    # === 🔥 115/01/14 [新增] 加密步驟 (在存檔前執行) ===
    # 使用 apply 對整欄進行加密
    # 確保轉成字串 (str) 再加密，避免數值型態報錯
    if 'ID' in res.columns:
        res['ID'] = res['ID'].apply(lambda x: CryptoManager.encrypt_deterministic(str(x)))
        
    if '姓名' in res.columns:
        res['姓名'] = res['姓名'].apply(lambda x: CryptoManager.encrypt_deterministic(str(x)))
    # ==========================================

    # 最後依照床位排序
    res = res.sort_values(by=['床位'], ascending=True)
    
    res.to_csv('interface/data/temp.csv', index=False, encoding='utf-8_sig')

def reorder():
    res = pd.read_csv('../data/temp.csv')
    res = res.sort_values(by=['床位'], ascending=True)
    row_indexes = res[res['床位'].apply(lambda x: x[0].isdigit())]
    res = res.drop(row_indexes.index)
    res.to_csv('interface/data/temp.csv', index=False, encoding='utf-8_sig', errors='ignore')
    
# ==========================================
# 3. 🔥 修正版：使用 DataFrame 處理 Decode + 加密
# ==========================================

# ==========================================
# 3. 🔥 直接從 API data_list 提取並解密的完美版
# ==========================================

# def fetch_decode_and_save(data_list):
#     if not data_list:
#         print("⚠️ [Decode] No data provided to process")
#         return

#     try:
#         # 1. 建立完整的欄位名稱清單 (51個原本欄位 + 11個新欄位)
#         # 這樣才能把 API 回傳的「純數值陣列」正確對應到有意義的欄位名稱
#         full_col_names = [
#             'ID', '姓名', '性別', '出生年月日', '年齡', '透析次數(本院)', '透析開始時間', '透析結束時間', '紀錄時間', '透析機編號', 
#             '床位', '體溫', '開始體溫', '透析前體重(kg)', '理想體重(kg)', '目標脫水量(L)', '輸液量(L)', '食物重量(kg)', '預估脫水量(L)', '設定脫水量(L)', 
#             '結束體重(kg)', '實際脫水量(L)', 'Start_SBP', 'Start_DBP', 'End_SBP', 'End_DBP', '透析模式', '透析器', '開始透析液流速', '開始血液流速', 
#             '透析液Ca：3.0', '傳導度：13.9', '血管通路', 'Heparin', 'ESA', '透析器凝血情況', '血壓(收縮)', '血壓(舒張)', '脈搏', '呼吸', 
#             '血流速(ml/min)', '透析液流速(ml/min)', '靜脈壓(mmHg)', '透析液壓(mmHg)', '膜上壓(mmHg)', '脫水速率', '累積量', '透析液溫度(℃)', '肝素注射量(ml/hr)', '沖水量(L)', 
#             '確認血管通路', 
#             # 👇 下面是 API 回傳在最後面的額外欄位
#             '血型', 'Rh', 'B型肝炎', 'C型肝炎', 'HIV', 'A+P', '約束', '跌倒風險', '飲食', 'nurse_record', '醫囑'
#         ]

#         # 2. 將 API 原始的 list of lists 轉換為 DataFrame
#         df_raw = pd.DataFrame(data_list)
        
#         # 動態對應欄位名稱 (避免 API 回傳長度不符導致報錯，只取實際有的長度)
#         actual_cols_count = len(df_raw.columns)
#         df_raw.columns = full_col_names[:actual_cols_count]

#         processed_rows = []
        
#         # 3. 現在有了欄位名稱，我們可以用 .get() 安全地逐行處理了！
#         for idx, row in df_raw.iterrows():
            
#             # 取得原始 ID 與 姓名 (去除空白)
#             raw_id = str(row.get('ID', '')).strip()
#             raw_name = str(row.get('姓名', '')).strip()
            
#             # 過濾邏輯 (若 ID 為空、不是數字、或是暫存床 0-9 開頭，則跳過)
#             if not raw_id or not raw_id.isdigit():
#                 continue
                
#             raw_bed = str(row.get('床位', ''))
#             if raw_bed and raw_bed[0].isdigit():
#                 continue

#             # 4. 加密 (Encrypt)
#             enc_id = CryptoManager.encrypt_deterministic(raw_id) if raw_id else ''
#             enc_name = CryptoManager.encrypt_deterministic(raw_name) if raw_name else ''

#             # 5. 組合需要的欄位 (如果 API 沒傳這個欄位，會安全地填入空字串)
#             new_row = {
#                 'case_number': enc_id,                  
#                 'name': enc_name,                       
#                 'age': row.get('年齡', ''),
#                 'birthday': row.get('出生年月日', ''),
#                 'blood_type': row.get('血型', ''),
#                 'blood_rh': row.get('Rh', ''),
#                 'hbv': row.get('B型肝炎', ''),
#                 'hcv': row.get('C型肝炎', ''),
#                 'hiv': row.get('HIV', ''),
#                 'a+p': row.get('A+P', ''),
#                 'constraint': row.get('約束', ''),
#                 'fall_risk': row.get('跌倒風險', ''),
#                 'fiber_list': row.get('飲食', ''),
#                 'nurse_record': row.get('nurse_record', ''), 
#                 'order': row.get('醫囑', '')
#             }
#             processed_rows.append(new_row)

#         # 6. 轉 DataFrame 並去除重複 (每個病患留最新一筆)
#         df_out = pd.DataFrame(processed_rows)
#         if not df_out.empty:
#             df_out = df_out.drop_duplicates(subset=['case_number'], keep='last')
        
#         # 7. 存檔
#         df_out.to_csv('interface/data/patient_data.csv', index=False, encoding='utf-8_sig')
        
#         print(f"✅ [Decode] Processed & Encrypted {len(df_out)} rows.")
#         print("📂 Saved to: interface/data/patient_data.csv")
        
#     except Exception as e:
#         print(f"❌ [Error] Failed to process data: {e}")   


def run():
    date = getNowDate()
    data = getAPIResponse(date)
    convertCSV(data)
    # try: 
    #     fetch_decode_and_save(data)
    # except Exception as e:
    #     print(f"⚠️ decode 失敗: {e}")

def fetchData():
    date = getNowDate()
    data = getAPIResponse(date)
    convertCSV(data)
    # try: 
    #     fetch_decode_and_save(data)
    # except Exception as e:
    #     print(f"⚠️ decode 失敗: {e}")