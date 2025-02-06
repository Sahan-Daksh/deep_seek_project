from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from main import send_request, process_file
import logging
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

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
        try:
            await websocket.send_text(message)
            logging.info(f"Message sent: {message[:100]}...")
        except Exception as e:
            logging.error(f"Error sending message: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message: {data[:100]}...")
            
            try:
                # Process message using Ollama via send_request
                response = send_request(data)
                logging.info(f"Response generated: {response[:100]}...")
                
                await manager.send_message(response, websocket)
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                logging.error(error_msg)
                await manager.send_message(error_msg, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), question: str = Form(...)):
    try:
        # Create file path in uploads directory
        file_path = os.path.join("uploads", file.filename)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logging.info(f"File saved: {file_path}")
        
        # Process file and generate response
        response = send_request(question, file_path)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        return {"response": response}
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return {"error": str(e)}