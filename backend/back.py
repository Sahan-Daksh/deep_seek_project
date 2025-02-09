from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from main import send_request, process_file  # Import from your existing main.py
import logging
import json
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("New client connected")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info("Client disconnected")

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_json({
            "response": message,
            "timestamp": str(datetime.now())
        })

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")
            file_path = data.get("file_path")

            result = send_request(prompt, file_path)
            await manager.send_message(result, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await manager.send_message(f"Error: {str(e)}", websocket)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), prompt: str = Form(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        result = send_request(prompt, file_path)
        
        # Clean up
        os.remove(file_path)

        return {
            "response": result,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logging.error(f"Error processing upload: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)