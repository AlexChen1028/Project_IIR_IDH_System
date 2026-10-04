import os
import datetime
import requests
import json
import pandas as pd
import time as time_module

# 115/01/14 update: 引入加密模組
# 直接引入，如果失敗就讓它報錯，這樣才知道問題在哪
from interface.utils import CryptoManager

# === [修正] API 請求設定 ===
API_TIMEOUT = 30        # API 請求超時秒數
API_MAX_RETRIES = 3     # 最大重試次數
API_RETRY_DELAY = 5     # 重試間隔秒數

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

    def get_now_date():
        """取得當前日期"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === [修正] 加入 timeout + retry 機制 ===
    response = None
    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            print(f"[Fetch API] 嘗試第 {attempt}/{API_MAX_RETRIES} 次請求... ({get_now_date()})")
            response = requests.get(url, params=param, timeout=API_TIMEOUT)
            response.raise_for_status()
            print(f"[Fetch API] 請求成功 (HTTP {response.status_code})")
            break
        except requests.exceptions.Timeout:
            print(f"⚠️ [Fetch API] 第 {attempt} 次請求超時 (>{API_TIMEOUT}秒)")
            if attempt < API_MAX_RETRIES:
                print(f"   等待 {API_RETRY_DELAY} 秒後重試...")
                time_module.sleep(API_RETRY_DELAY)
            else:
                print(f"❌ [Fetch API] 已達最大重試次數，放棄請求")
                return []
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ [Fetch API] 第 {attempt} 次連線失敗: {e}")
            if attempt < API_MAX_RETRIES:
                print(f"   等待 {API_RETRY_DELAY} 秒後重試...")
                time_module.sleep(API_RETRY_DELAY)
            else:
                print(f"❌ [Fetch API] 已達最大重試次數，放棄請求")
                return []
        except requests.exceptions.RequestException as e:
            print(f"❌ [Fetch API] 請求異常: {e}")
            return []

    if response is None:
        return []

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
            
            print(f"[Fetch API] 資料儲存成功，共 {len(data_list)} 筆紀錄")
        
        except Exception as error:
            data_list = []
            print(f"❌ [Fetch API] 解析錯誤: {error}")
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


def run():
    date = getNowDate()
    data = getAPIResponse(date)
    convertCSV(data)

def fetchData():
    date = getNowDate()
    data = getAPIResponse(date)
    convertCSV(data)
