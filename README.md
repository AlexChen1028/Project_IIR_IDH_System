# IDH 預測系統

透析中低血壓 (Intradialytic Hypotension, IDH) 預警系統：Django 網頁介面 + 深度學習 / EBM 預測模型。

> 本倉庫已去識別化，**不含**任何病患資料、資料庫、加密金鑰、模型權重與內網位址。

## 設定 (環境變數)
| 變數 | 說明 |
|---|---|
| `DJANGO_SECRET_KEY` | Django 金鑰 |
| `DJANGO_ALLOWED_HOSTS` | 以逗號分隔 |
| `HOSPITAL_API_URL` | 醫院透析資料 API |
| `OLLAMA_BASE_URL` | LLM 服務位址 |

`interface/utils.py` 首次執行會自動產生 `secret.key`（已加入 .gitignore，請勿上傳）。

## 未包含的檔案
- 模型權重 (`interface/weights/*.zip|*.pth|*.joblib`)：請自行訓練或向作者索取
- `static/js/highcharts.js`：請至 Highcharts 官網下載（注意授權）
- `interface/data/`、`db.sqlite3`：含病患資料

## 執行
```
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
