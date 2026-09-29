function runTime() {
  let now = new Date();
  let timeDiv = document.getElementById("currentTime");
  let nowY = now.getFullYear();
  let nowM = now.getMonth() + 1;
  let nowD = now.getDate();
  let nowW = now.getDay();
  let nowH = now.getHours();
  let nowI = now.getMinutes();
  let nowS = now.getSeconds();

  if (nowH < 10) {
    nowH = "0" + nowH;
  }
  if (nowI < 10) {
    nowI = "0" + nowI;
  }
  if (nowS < 10) {
    nowS = "0" + nowS;
  }
  switch (nowW) {
    case 0:
      nowW = "日";
      break;
    case 1:
      nowW = "一";
      break;
    case 2:
      nowW = "二";
      break;
    case 3:
      nowW = "三";
      break;
    case 4:
      nowW = "四";
      break;
    case 5:
      nowW = "五";
      break;
    case 6:
      nowW = "六";
      break;
  }

  // let nowStr =
  //   nowY +
  //   " 年 " +
  //   nowM +
  //   " 月 " +
  //   nowD +
  //   " 日 星期" +
  //   nowW +
  //   "  " +
  //   nowH +
  //   ":" +
  //   nowI +
  //   ":" +
  //   nowS;
  // timeDiv.innerText = nowStr;
}

runTime();
setInterval(runTime, 1000);

function refresh() {
  window.location.reload();
}
setInterval(refresh, 180000);

rootUrl = "http://127.0.0.1:8000/index/";
// const rootUrl = "http://127.0.0.1:8080/index/";

// Left panel
function openTab(evt, tabName, area) {
  document.location.href = rootUrl + area;
}

function openNurseArea(){
  console.log("open nurse area.");
  document.location.href = rootUrl + 'Y';
}

// const bed = [
//   "A1", "A2", "A3", "A5", "A6", "A7", "A8", "A9",
//   "B1", "B2", "B3", "B5", "B6", "B7", "B8", "B9",
//   "C1", "C2", "C3", "C5", "C6", "C7", "C8", "C9",
//   "D1", "D2", "D3", "D5", "D6", "D7", "D8", "D9",
//   "E1", "E2", "E3", "E5", "E6", "E7", "E8",
//   "I1", "I2",
// ];
// const modal = document.getElementById("modal");
window.onclick = function (event) {
  if (event.target.id == "modal") {
    clear();
  // } else if(event.target.id == "feedbackModal"){
  //   document.getElementById("feedbackModal").classList.toggle("hidden");
  } else if(event.target.id == "warningModal"){
    document.getElementById("warningModal").classList.toggle("hidden");
  } else if(event.target.id == "exportFileModal"){
    document.getElementById("exportFileModal").classList.toggle("hidden");
  }
};

function openExportFileModal() {
  document.getElementById("exportFileModal").classList.toggle("hidden");
}

function closeModal() {
  console.log('closemodal');
  clear();
}
flag = true;
function next() {

  if (flag) {
    flag = false;
    document.getElementById("patient2").innerText = document.getElementById("patient").innerText;
    document.getElementsByClassName("modal-left")[0].style.display = "none";
    document.getElementsByClassName("modal-right")[0].style.display = "none";
    document.getElementsByClassName("modal-table")[0].classList.remove("hidden");
    document.getElementById("left").src = "/static/img/left_active.svg";
    document.getElementById("right").src = "/static/img/right_inactive.svg";
  }
}

function prev() {
  if (!flag) {
    flag = true;
    document.getElementsByClassName("modal-left")[0].style.display = "flex";
    document.getElementsByClassName("modal-right")[0].style.display = "flex";
    document.getElementsByClassName("modal-table")[0].classList.add("hidden");
    document.getElementById("left").src = "/static/img/left_inactive.svg";
    document.getElementById("right").src = "/static/img/right_active.svg";
  }
}

// === 這裡是關鍵：clear() 不再 redirect 回首頁 ===
function clear() {
  console.log("clear");
  const back = document.location.href;
  const area = back.split("/");

  if (area[4] == "get_record") {
    // feedback.html 的 modal：把已勾選的處置暫存到 hidden，再單純關 modal
    const tmp_form = document.getElementById("idh-tmp-form");
    const sign_checked = document.querySelectorAll("[type=radio]:checked");
    const treatment_checked = document.querySelectorAll("[type=checkbox]:checked");
    let tmp_list = "";

    for (let i = 0; i < sign_checked.length; i++) {
      const p_id = sign_checked[i].name.split("-");
      tmp_list = tmp_list + p_id[1] + "-" + sign_checked[i].value;
      for (let j = 0; j < treatment_checked.length; j++) {
        const tmp_id = treatment_checked[j].name.split("-")[1];
        if (tmp_id == p_id[1]) {
          tmp_list = tmp_list + "+" + treatment_checked[j].value;
        }
      }
      tmp_list += "/";
    }

    if (tmp_form) tmp_form.value = tmp_list;
    console.log(tmp_list);
    const modalEl = document.getElementById("modal");
    if (modalEl) modalEl.classList.add("hidden");

  } else {
    // 首頁 / 其他頁：關 modal 與內部 layout，然後回首頁
    const modalEl = document.getElementById("modal");
    if (modalEl) modalEl.classList.add("hidden");

    const modalLeft = document.getElementsByClassName("modal-left")[0];
    const modalRight = document.getElementsByClassName("modal-right")[0];
    const modalTable = document.getElementsByClassName("modal-table")[0];

    if (modalLeft && modalRight && modalTable) {
      modalLeft.style.display = "flex";
      modalRight.style.display = "flex";
      modalTable.classList.add("hidden");
    }

    const leftIcon = document.getElementById("left");
    const rightIcon = document.getElementById("right");
    if (leftIcon && rightIcon) {
      leftIcon.src = "/static/img/left_inactive.svg";
      rightIcon.src = "/static/img/right_active.svg";
    }

    flag = true;

    // ⭐ 關閉內容後回首頁（立即重整）
    window.location.href = rootUrl + "dashboard";  // 或 rootUrl + area[5]
  }
}


// let chart, xAxis, SBP, pulse, CVP, exist, linechart, bands;
// let linecharts = [];

function changeStatus(bed_id) {
  let bed = document.getElementById(bed_id);
  bed_num = bed_id.split('-')[1];
  let idh_bed = document.getElementById("idh-patients-list");
  if(sessionStorage.getItem("orangeList") == null){
    sessionStorage.setItem("orangeList", "[]");
    sessionStorage.setItem("yellowList", "[]");
  }
  if (bed.classList.contains("bed-feedback-active")) {
    idh_bed.value = idh_bed.value.replace(bed_num + '-', "");
    bed.classList.toggle("bed-feedback-active");
    console.log(idh_bed);
  } else if(bed.classList.contains("bed-feedback-active-20ver")){
    idh_bed.value = idh_bed.value.replace(bed_num + '-', "");
    let listTmp = JSON.parse(sessionStorage.getItem("yellowList"));
    if(!listTmp.includes(bed_num)){
      listTmp.push(bed_num);
    }
    sessionStorage.setItem("yellowList", JSON.stringify(listTmp));
    bed.classList.toggle("bed-feedback-active-20ver");
  } else if(bed.classList.contains("bed-feedback-active-bothver")){
    idh_bed.value = idh_bed.value.replace(bed_num + '-', "");
    let listTmp = JSON.parse(sessionStorage.getItem("orangeList"));
    if(!listTmp.includes(bed_num)){
      listTmp.push(bed_num);
    }
    sessionStorage.setItem("orangeList", JSON.stringify(listTmp));
    bed.classList.toggle("bed-feedback-active-bothver");
  } else {
    let yellowTmp = JSON.parse(sessionStorage.getItem("yellowList"));
    let orangeTmp = JSON.parse(sessionStorage.getItem("orangeList"));
    if(yellowTmp.includes(bed_num)){
      bed.classList.toggle("bed-feedback-active-20ver");
    } else if(orangeTmp.includes(bed_num)){
      bed.classList.toggle("bed-feedback-active-bothver");
    } else{
      bed.classList.toggle("bed-feedback-active");
    }
    idh_bed.value += bed_num + "-";
    console.log(idh_bed);
  }
}

function SwitchNurseList() {
  targetUrl = rootUrl + `NurseArea/NurseList`;
  location.href = targetUrl;
}

function SwitchRandomCodeDisplay(){
  let allRedCheckList = $('img.redCheck');
  for(let i=0; i<allRedCheckList.length; ++i){
    if(allRedCheckList[i].hidden == true){
      allRedCheckList[i].hidden = false;
    } else {
      allRedCheckList[i].hidden = true;
    }
  }
}

// 護理師處置時間
document.addEventListener("DOMContentLoaded", function() {
  const handleSelect = document.getElementById("handle-select");
  const handleTime = document.getElementById("handle-time");
  
  // Generate times in 15-minute intervals
  const interval = 5; // Interval in minutes
  const now = new Date();
  const currentHours = now.getHours();
  const currentMinutes = now.getMinutes();
  let defaultTime = "";

  // Populate the select options
  for (let hour = 0; hour <= currentHours; hour++) {
      for (let minute = 0; minute < 60; minute += interval) {
          if (hour === currentHours && minute > currentMinutes) break; // Stop if time exceeds current time
          
          const time = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
          const option = document.createElement("option");
          option.value = time.replace(":", ""); // For easier handling in JS
          option.textContent = time;
          handleSelect.appendChild(option);
          
          // Set default time to current time
          if (hour === currentHours && minute <= currentMinutes) {
            defaultTime = time; // Store the value for the default time
          }
      }
  }
  handleTime.value = defaultTime;
  
});

function HandleTimeAppend(){
  
  let handle_time = document.getElementById(`handle-time`);  //input text
  let selected_handle_time = document.getElementById(`handle-select`).value; //selected time

  // current_time = selected_handle_time.replace(":", "");
  handle_time.value = selected_handle_time.slice(0,2)+":"+selected_handle_time.slice(2);
  
  
  return;
}

// blinking
originalTitle = document.title;  // 儲存原本的標題
// blinkInterval;  // 儲存標題閃爍的定時器ID
// alertInterval;  // 儲存圖示閃爍的定時器ID
isTabVisible = true;

originalFavicon = "/static/img/kidney.svg"; // 原本的圖示
alertFavicon = "/static/img/kidney_warning.svg"; // 警告圖示

// 開始閃爍標題
function startBlinkingTitle() {
    if (!blinkInterval) {
        blinkInterval = setInterval(() => {
            document.title = document.title === originalTitle ? " 請查看此頁面！ ⏳" : originalTitle;
        }, 1000);  // 每1秒變更一次
    }
}

// 停止閃爍標題
function stopBlinkingTitle() {
    clearInterval(blinkInterval);
    blinkInterval = null;
    document.title = originalTitle;
}

// 創建/切換圖示
function createFavicon(href) {
    const existingFavicon = document.getElementById("favicon");
    if (existingFavicon) {
        existingFavicon.remove();
    }
    const newFavicon = document.createElement("link");
    newFavicon.id = "favicon";
    newFavicon.rel = "icon";
    newFavicon.href = href;
    newFavicon.type = "image/x-icon";
    document.head.appendChild(newFavicon);
}

// 開始閃爍圖示
function startFaviconAlert() {
    if (!alertInterval) {
        alertInterval = setInterval(() => {
            const currentFavicon = document.getElementById("favicon").href;
            createFavicon(currentFavicon.includes("kidney.svg") ? alertFavicon : originalFavicon);
        }, 100);  // 圖示閃爍間隔
    }
}

// 停止閃爍圖示
function stopFaviconAlert() {
    clearInterval(alertInterval);
    alertInterval = null;
    createFavicon(originalFavicon);
}

// 檢查是否有 .alert-trigger 元素並根據需要啟動或停止特效
function checkForAlertTrigger() {
    const alertElement = document.querySelector('.danger-bg');
    if (alertElement && document.hidden) {
      console.log(alertElement);
        startBlinkingTitle();
        startFaviconAlert();
    } else {
        stopBlinkingTitle();
        stopFaviconAlert();
    }
}

// 當頁面進入背景或變為可見時觸發檢查
document.addEventListener("visibilitychange", function() {
    isTabVisible = !document.hidden;
    checkForAlertTrigger();
});

// 定期檢查 `.alert-trigger` 是否出現
setInterval(checkForAlertTrigger, 1000);  // 每秒檢查一次

// 頁面載入時設置初始圖示
document.addEventListener("DOMContentLoaded", function() {
  createFavicon(originalFavicon);
});

// 12/31 新增：自動觸發反饋表單的床位點擊
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const triggerBed = urlParams.get('auto_click');
    
    if (triggerBed) {
        console.log("準備自動觸發床位:", triggerBed);
        
        // 清除網址參數
        const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.replaceState({path: newUrl}, '', newUrl);
        
        // 【修改點 1】延遲時間加長到 1000 毫秒 (1秒)，確保 jQuery 事件已綁定
        setTimeout(() => {
            const bedElem = document.getElementById('bed-' + triggerBed);
            
            if (bedElem) {
                console.log("執行第 1 次點擊...");
                bedElem.click(); 

                // 【修改點 2】過 100 毫秒後再點一次 (模擬雙擊，或確保狀態切換)
                setTimeout(() => {
                    console.log("執行第 2 次點擊 (確保視窗開啟)...");
                    bedElem.click();
                }, 200);
            } else {
                console.warn("找不到床位元素: bed-" + triggerBed);
            }
        }, 1000); 
    }
});

// ==========================================
//  105/02/06 新增：EBM 整合與點擊處理函式
// ==========================================

// 1. 開啟警告處置視窗 (EBM 或 舊模型高風險)
function OpenWarningModal(bed, name, sbp, dbp) {
  const modal = document.getElementById("warningModal");
  if (!modal) return;

  // 填入病患資訊到 Modal
  document.getElementById("patientBed").innerText = bed;
  document.getElementById("patientName").innerText = name;
  
  // 自動填入當前血壓 (若有欄位)
  const sbpInput = document.getElementById("SBP");
  const dbpInput = document.getElementById("DBP");
  if (sbpInput) sbpInput.value = sbp;
  if (dbpInput) dbpInput.value = dbp;

  // 顯示視窗
  modal.classList.remove("hidden");
}

// 2. 核心點擊函式 (接收 HTML onclick 傳來的參數)
function ClickOnPatient(bed, idh, name, status, done, first, sbp, dbp, random, isEbm) {
  console.log("ClickOnPatient Triggered");
  console.log(`Bed: ${bed}, IDH: ${idh}, EBM: ${isEbm}, Random: ${random}, Done: ${done}`);

  // 資料型態轉換 (Python 傳來的是字串 'True'/'False' 或 '1'/'0')
  const isEbmWarning = (isEbm === 'True' || isEbm === true);
  const isDone = (done === 'True' || done === true);
  const isRandomOne = (parseInt(random) === 1);
  const prob = parseInt(idh);

  // === 判斷是否開啟警告處置視窗 ===
  // 條件：(是 EBM 警告 或 舊模型高風險) 且 (尚未處置)
  // 注意：舊模型門檻通常設為 50%，需與 views.py 一致
  if ( (isEbmWarning || (prob >= 50 && isRandomOne)) && !isDone ) {
      console.log("⚠️ 觸發高風險警示視窗");
      OpenWarningModal(bed, name, sbp, dbp);
  } else {
      // === 否則：跳轉到詳細資訊頁面 ===
      console.log("ℹ️ 跳轉至詳細頁面");
      // 根據當前 URL 判斷所在區域 (預設為 dashboard)
      let currentArea = "dashboard";
      if (window.location.href.includes("tabA")) currentArea = "A";
      if (window.location.href.includes("tabB")) currentArea = "B";
      
      // 跳轉路徑 (rootUrl 已經在 index.js 上方定義過)
      // 路徑格式: /index/get_detail/<area>/<bed>/<idh>
      window.location.href = rootUrl + "get_detail/" + currentArea + "/" + bed + "/" + idh;
  }
}