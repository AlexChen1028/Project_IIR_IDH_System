# IDH 預警系統 (Intradialytic Hypotension Early Warning System)

大三專題：針對血液透析病人的**透析中低血壓 (IDH)** 預警系統。系統會即時抓取透析資料、用機器學習模型預測 IDH 風險，並在護理人員的網頁儀表板上顯示警示。

> 本倉庫已去識別化，**不含**任何病患資料、資料庫、加密金鑰、模型權重與內網位址。

## 專題背景

血液透析過程中，病人可能因為脫水速度過快等原因發生血壓驟降（IDH），造成不適甚至危險。護理人員同時照顧多床病人，很難隨時掌握每個人的風險。本系統希望做到：

- 在透析**開始前與進行中**預測每位病人發生 IDH 的機率
- 把高風險病人**即時標示**在儀表板上，提醒護理人員提早處理
- 收集護理人員對警示的**回饋與處置紀錄**，作為後續改進的依據

## 主要功能

- **風險儀表板**：依透析區域與床位顯示所有病人的 IDH 風險等級（安全 / 警告 / 危險），並顯示血壓、心跳、靜脈壓等趨勢圖
- **護理人員責任區**：可設定每位護理人員負責的床位，只看自己照顧的病人
- **警示與回饋**：護理人員可確認警示、記錄處置方式（用藥、輸液、護理措施、機器設定調整等），以及回報實際發生 IDH 的時間
- **LLM 病況摘要**：把病人今日數據與前 12 次透析的歷史統計比對，交給本地 LLM（透過 Ollama）產生摘要，輔助護理人員判讀
- **資料匯出**：匯出警示與回饋紀錄
- **隱私保護**：病人姓名與病歷號在資料庫中以加密方式儲存（見 `interface/utils.py`）

## 預測模型

| 模型 | 位置 | 用途 |
|---|---|---|
| EBM (Explainable Boosting Machine) | `interface/model/EBM.py` | 用 16 個透析前特徵（性別、年齡、近 7 / 28 天 IDH 次數、起始血壓、脈搏、體重、目標脫水量、血流速等）預測風險，可解釋各特徵的貢獻；輸出再經 Isotonic Regression **機率校準** |
| Transformer | `interface/model/prediction.py`、`interface/weights/transformer_model.py` | 以透析過程中的時間序列紀錄（血壓、脈搏、透析機參數等）預測 IDH |
| GRU | `interface/weights/gru_model.py` | 另一種時間序列模型 |

**IDH 判定標準**：透析前收縮壓 < 160 mmHg 時，透析中收縮壓 < 90 mmHg 即算 IDH；透析前收縮壓 ≥ 160 mmHg 時，門檻為 100 mmHg（Nadir 90 / 100 定義，見 `interface/model/EBM.py`）。

## 系統架構

```
醫院透析資料 API ──(每 5 分鐘 cron)──> scripts/fetch_API.py ──> CSV ──> SQLite 資料庫
                                                                  │
                          EBM / Transformer 模型 <─────────────────┤
                                     │                            │
                                     └────────> Django 網頁儀表板 <┘
                                                  (+ Ollama LLM 摘要)
```

- 後端：Django 5、django-crontab（排程抓資料）
- 模型：PyTorch（Transformer / GRU）、scikit-learn（Isotonic Regression 校準）、joblib（載入 EBM 模型）
- 前端：Django Template、JavaScript、Highcharts
- LLM：LangChain + Ollama

## 目錄結構

```
idh/                 Django 專案設定
interface/
  models.py          資料表：Patient、Dialysis、Record、Predict、Warnings、Feedback、Nurse
  views.py           儀表板、警示、回饋、匯出等後端邏輯
  urls.py            路由
  utils.py           姓名 / 病歷號加解密
  model/             EBM 與 Transformer 預測流程
  weights/           模型架構定義（權重檔未上傳）
  templates/         頁面模板
scripts/             抓取 API、建立資料庫、載入資料
static/              CSS、JS、圖示
train_calibration.py 訓練機率校準模型
check_calibration.py 檢查校準模型
count_number.py      統計資料集中的 IDH 數量
ERdiagram*.drawio    資料庫 ER 圖
```

## 環境設定

| 環境變數 | 說明 |
|---|---|
| `DJANGO_SECRET_KEY` | Django 金鑰 |
| `DJANGO_ALLOWED_HOSTS` | 允許的主機，以逗號分隔 |
| `HOSPITAL_API_URL` | 透析資料 API 位址 |
| `OLLAMA_BASE_URL` | Ollama LLM 服務位址 |

`interface/utils.py` 首次執行時會自動產生加密用的 `secret.key`（已列入 `.gitignore`，**請勿上傳**）。

## 執行方式

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 未包含的檔案

基於隱私與授權考量，下列檔案未上傳，需自行準備：

- 模型權重（`interface/weights/` 下的 `.zip`、`.pth`、`.joblib`）：需自行訓練
- `static/js/highcharts.js`：請至 [Highcharts 官網](https://www.highcharts.com/) 下載（注意授權條款）
- `interface/data/`、`db.sqlite3`：含病患資料，不公開

`requirements.txt` 尚未列出 scikit-learn 等部分套件，執行前可能需另行安裝。因此直接 clone 下來無法完整執行，本倉庫主要用於展示專題的系統設計與程式碼。
