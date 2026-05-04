import requests
import uuid
import platform
import threading

def send_analytics():
    def _thread_task():
        try:
            hwid = str(uuid.getnode()) 
            
            data = {
                "user_id": hwid,
                "version": "1.4.0",
                "os": f"{platform.system()} {platform.release()}"
            }
            
            requests.post("http://45.81.253.48:8000/report", json=data, timeout=5)
        except Exception:
            pass

    threading.Thread(target=_thread_task, daemon=True).start()

send_analytics()