cd /d "C:\Users\hp\PycharmProjects\testAiPradavan"
chcp 65001
"C:\Users\hp\AppData\Local\Programs\Python\Python312\python.exe" -m pytest -s integration_check_for_clients/test_integrations_report.py >> integration_log.txt 2>&1
pause
