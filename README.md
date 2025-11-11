# TY_address_finder_web
address finder deploy on colud   
Cloud Platform: google cloud console  


## How to turn the python program to cloud-running version
1. Add the flask to python program  
2. Add the necessery cloud function  
>* Chrome and driver check  
>* Logging  
>* Auto ping (avoid cold start)  
>* HTML template (Include style.css, function.js) 
3. Add the cloud environment files  
>* Dockerfile, requirements.txt  
4. Push to Github

## How to deploy on Google Cloud

1. Switch to Google Cloud Console  
2. 新增專案 > 部屬應用程式
3. 部屬Web服務 > 連結存放居 > 連結Github容器
4. 與 Origin master建立連結後便會刷新建構 
5. 查看建構(Build)狀況是否成功。
6. 至部署完成網址測試，並查看記錄檔(logging)是否正確


## Difficulities to solve

1. 環境建置(environment)
>* 反覆的用ChatGPT確認，後來由Copilot CLI反覆重建、測試至完成。
>* 部署前用桌面Docker完成本地次測試，成功再Push。

2. 雲端硬體設置，記憶體(Memory Exceed)
>* 原設512Mb，logging有超量警示，調整成1Gb
>>* 編輯及部屬新的修訂版本 > 編輯容器 > 資源(Memory、CPU)
>* 有用Threading但還是1CPU足矣

3. 避免冷啟動(約10秒啟動時間)
>* Auto Ping 
>>* Cloud Schedule API
>>* 網址/ping
>>* Per 240 sec.



