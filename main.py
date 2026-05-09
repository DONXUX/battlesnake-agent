import threading
import time
import os

if __name__ == '__main__':
    # Fastapi 앱을 별도의 스레드에서 실행
    def run_fastapi():
        os.system('python main.py')

    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

