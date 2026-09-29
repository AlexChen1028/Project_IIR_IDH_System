import pandas as pd
from datetime import datetime
from tqdm import tqdm

class CSV:
    def __init__(self, path):
        self.file = path

    def read_to_patient(self):
        usecols= ['ID', '姓名', '性別', '出生年月日']
        df = pd.read_csv(self.file, usecols=usecols)
        tqdm_iter = tqdm(df.iterrows(), total=len(df), desc='Patient')
        for idx, row in tqdm_iter:
            pass  # 這裡可以加 row 處理邏輯
        df['出生年月日'] = df['出生年月日'].apply(lambda x: datetime.strptime(str(x), '%Y-%m-%d').date())
        df = df.drop_duplicates()                     # drop duplicates
        df.to_csv('interface/data/patient.csv', encoding='utf_8_sig')    
    
    def read_to_dialysis(self):
        usecols = ['ID', '年齡', '透析次數(本院)', '透析開始時間', '透析結束時間', '透析機編號', '床位', '體溫', '開始體溫', '透析前體重(kg)', '理想體重(kg)', '目標脫水量(L)', '輸液量(L)' , '食物重量(kg)', '預估脫水量(L)', '設定脫水量(L)', '結束體重(kg)', '實際脫水量(L)', 'Start_SBP', 'Start_DBP', 'End_SBP', 'End_DBP', '透析模式', '透析器', '開始透析液流速', '開始血液流速', '透析液Ca：3.0', '傳導度：13.9', '血管通路', 'Heparin', 'ESA', '透析器凝血情況']
        df = pd.read_csv(self.file, usecols=usecols)
        tqdm_iter = tqdm(df.iterrows(), total=len(df), desc='Dialysis')
        for idx, row in tqdm_iter:
            pass  # 這裡可以加 row 處理邏輯
        df['透析開始時間'] = df['透析開始時間'].apply(lambda x: pd.to_datetime(x))
        df['透析結束時間'] = df['透析結束時間'].apply(lambda x: pd.to_datetime(x))
        # df['床位'] = df['床位'].apply(lambda x: x if x[0].isdigit() == False else x[::-1])   # reverse bed_id
        df = df.fillna(-1)
        df = df.drop_duplicates()                     # drop duplicates
        df = df[usecols]
        # print(df.info())
        df.to_csv('interface/data/dialysis.csv', encoding='utf_8_sig') 

    def read_to_record(self):
        usecols = ['ID', '透析次數(本院)', '紀錄時間', '血壓(收縮)', '血壓(舒張)', '脈搏', '呼吸', '血流速(ml/min)', '透析液流速(ml/min)', '靜脈壓(mmHg)', '透析液壓(mmHg)', '膜上壓(mmHg)', '脫水速率', '累積量', '透析液溫度(℃)', '肝素注射量(ml/hr)', '沖水量(L)', '確認血管通路']
        df = pd.read_csv(self.file, usecols=usecols)
        tqdm_iter = tqdm(df.iterrows(), total=len(df), desc='Record')
        for idx, row in tqdm_iter:
            pass  # 這裡可以加 row 處理邏輯
        df['紀錄時間'] = df['紀錄時間'].apply(lambda x: pd.to_datetime(x))
        df['沖水量(L)'] = pd.to_numeric(df['沖水量(L)'],errors="coerce")
        df = df.fillna(-1)
        df = df.drop_duplicates()                     # drop duplicates
        # df.info()
        df.to_csv('interface/data/record.csv', encoding='utf_8_sig') 

    # def read_to_patient_data(self):
    #     """
    #     [新增] 讀取 temp.csv，解密並萃取特定欄位，產生 patient_data.csv
    #     """
    #     from interface.utils import CryptoManager # 確保有引入加密模組
        
    #     # 這是您在 fetch_decode_and_save 中需要的欄位
    #     # 注意：temp.csv 的欄位名稱是中文的，我們需要讀取這些中文欄位
    #     try:
    #         # 讀取整個 temp.csv，因為欄位比較雜，乾脆全讀再挑
    #         df_temp = pd.read_csv(self.file)
            
    #         processed_rows = []
    #         tqdm_iter = tqdm(df_temp.iterrows(), total=len(df_temp), desc='Patient Data (Decode)')
            
    #         for idx, row in tqdm_iter:
    #             raw_id = str(row.get('ID', '')).strip()
    #             raw_name = str(row.get('姓名', '')).strip()
                
    #             # 如果是無效的 ID 或是暫存床，直接跳過 (防呆)
    #             if not raw_id or str(row.get('床位', '')).startswith(('0','1','2','3','4','5','6','7','8','9')):
    #                 continue

    #             # 重新加密 (因為 temp.csv 裡的 ID 可能已經是加密過的了，這裡要特別小心)
    #             # ==========================================================
    #             # 💡 關鍵注意：如果 fetch_API.py 存入 temp.csv 時已經加密過，
    #             # 這裡就 *不需要* 再次加密！可以直接取用。
    #             # 這裡我假設 temp.csv 裡的 ID/姓名 已經是加密過的 (如您的 fetch_API 所示)
    #             # ==========================================================
                
    #             new_row = {
    #                 'case_number': raw_id,        # 已經加密過的 ID
    #                 'name': raw_name,             # 已經加密過的姓名
    #                 'age': row.get('年齡', ''),
    #                 'birthday': row.get('出生年月日', ''),
    #                 'blood_type': row.get('血型', ''), # 如果 temp 裡面沒有這個欄位，會填入 NaN
    #                 'blood_rh': row.get('Rh', ''),
    #                 'hbv': row.get('B型肝炎', ''),
    #                 'hcv': row.get('C型肝炎', ''),
    #                 'hiv': row.get('HIV', ''),
    #                 'a+p': row.get('A+P', ''),
    #                 'constraint': row.get('約束', ''),
    #                 'fall_risk': row.get('跌倒風險', ''),
    #                 'fiber_list': row.get('飲食', ''),
    #                 'nurse_record': row.get('nurse_record', ''), # 確認 temp.csv 裡有沒有這個欄位
    #                 'order': row.get('醫囑', '')
    #             }
    #             processed_rows.append(new_row)

    #         # 轉成 DataFrame 並去重覆 (如果同個病人有多筆，可能只需要留一筆)
    #         df_patient_data = pd.DataFrame(processed_rows)
    #         # 可以根據 case_number 去除重複
    #         df_patient_data = df_patient_data.drop_duplicates(subset=['case_number'], keep='last')
            
    #         # 存檔
    #         df_patient_data.to_csv('interface/data/patient_data.csv', index=False, encoding='utf_8_sig')
            
    #     except Exception as e:
    #         print(f"❌ [Error] Failed to create patient_data.csv: {e}")


def run():
    data = CSV('interface/data/temp.csv')
    data.read_to_patient()
    print("Patient data processed.")
    data.read_to_dialysis()
    print("Dialysis data processed.")
    data.read_to_record()
    print("Record data processed.")

    # [新增]
    # data.read_to_patient_data()
    # print("Patient Data (Decoded) processed.")

def splitCSV():
    steps = ["Patient", "Dialysis", "Record"]
    data = CSV('interface/data/temp.csv')
    for step in tqdm(steps, desc="splitCSV steps"):
        if step == "Patient":
            data.read_to_patient()
        elif step == "Dialysis":
            data.read_to_dialysis()
        elif step == "Record":
            data.read_to_record()
        # [新增]
        # elif step == "PatientData":
        #     data.read_to_patient_data()
