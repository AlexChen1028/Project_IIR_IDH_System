function TimeAppend(p_id){
    console.log(p_id);
    let idh_time_list = document.getElementById(`idh-time-${p_id}`);
    let idh_time = document.getElementById(`idh-select-${p_id}`).value;
    if (!idh_time) {
        return;  // 沒選時間就不做事
    }

    let current_time = idh_time.replace(":", "");
    let current_time_set = new Set(
        idh_time_list.value ? idh_time_list.value.split(",") : []
    );

    if (current_time_set.has(current_time)) {
        current_time_set.delete(current_time);
        idh_time_list.value = [...current_time_set].join(",");
    } else {
        current_time_set.add(current_time);
        idh_time_list.value = [...current_time_set].join(",");
    }

    // ⬇ 新增：時間有變動就展開右側處置區塊
    const rightPanel = document.getElementById(`feedback-right-${p_id}`);
    if (rightPanel) {
        rightPanel.classList.remove("hidden");
    }
}

// 12/31 新增：反饋表單的非同步提交
document.addEventListener('DOMContentLoaded', function() {
    const confirmBtn = document.getElementById('confirmFeedbackBtn');
    const feedbackForm = document.querySelector('#feedbackModal form');

    if (confirmBtn && feedbackForm) {
        confirmBtn.addEventListener('click', function(e) {
            e.preventDefault(); // ★ 這一行救命！它阻止了原本會導向 127.0.0.1 的動作
            
            if (!feedbackForm.checkValidity()) {
                feedbackForm.reportValidity();
                return;
            }

            const formData = new FormData(feedbackForm);

            fetch('/post_feedback/', {
                method: 'POST',
                body: formData,
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // ★ 關鍵：這裡是用相對路徑，所以會乖乖留在 localhost
                    const targetUrl = '/index/dashboard?auto_click=' + (data.bed_code || '');
                    window.location.href = targetUrl;
                } else {
                    alert('儲存失敗: ' + (data.msg || '未知錯誤'));
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }
});