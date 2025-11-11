// main.js - extracted from templates/index.html

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const textToCopy = element.textContent;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                alert('已複製到剪貼簿：' + textToCopy);
            })
            .catch(err => {
                console.error('複製失敗:', err);
                fallbackCopyToClipboard(textToCopy);
            });
    } else {
        fallbackCopyToClipboard(textToCopy);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        alert('已複製到剪貼簿：' + text);
    } catch (err) {
        console.error('回退複製失敗:', err);
        alert('無法自動複製，請手動複製：\n' + text);
    }
    document.body.removeChild(textArea);
}

document.addEventListener('DOMContentLoaded', () => {
    const searchButton = document.getElementById('searchButton');
    const addressInput = document.getElementById('addressInput');
    const resultDisplay = document.getElementById('resultDisplay');
    const errorMessage = document.getElementById('errorMessage');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const buttonText = document.getElementById('buttonText');

    searchButton.addEventListener('click', async () => {
        const address = addressInput.value.trim();

        // 重置顯示
        resultDisplay.classList.add('hidden');
        errorMessage.classList.add('hidden');
        errorMessage.textContent = '';

        if (!address) {
            errorMessage.textContent = '請輸入一個地址進行查詢。';
            errorMessage.classList.remove('hidden');
            return;
        }

        // 顯示載入狀態
        buttonText.textContent = '查詢中...';
        loadingSpinner.classList.remove('hidden');
        searchButton.disabled = true;

        try {
            const response = await fetch(`/search_address_api?address=${encodeURIComponent(address)}`);
            const data = await response.json();

            if (response.ok) {
                document.getElementById('simplifiedAddress').textContent = data.simplified_address;
                document.getElementById('formattedSimplifiedAddress').textContent = data.formatted_simplified_address;
                resultDisplay.classList.remove('hidden');
            } else {
                errorMessage.textContent = `錯誤：${data.error || '未知錯誤'}`;
                errorMessage.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Fetch error:', error);
            errorMessage.textContent = `網路或伺服器錯誤：${error.message}`;
            errorMessage.classList.remove('hidden');
        } finally {
            buttonText.textContent = '查詢地址';
            loadingSpinner.classList.add('hidden');
            searchButton.disabled = false;
        }
    });
});
