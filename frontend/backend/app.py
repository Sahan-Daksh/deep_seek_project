# filepath: /C:/Users/lakit/Desktop/DeepSeek_project/backend/app.py
from fastapi import FastAPI, WebSocket, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import requests
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.post("/ask")
async def ask(question: str = Form(...), file: UploadFile = File(None)):
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        # Process the file as needed
        response = requests.post('http://localhost:default_port/deepseek', files={'file': open(file_path, 'rb')})
        result = response.json()
    else:
        # Handle normal question
        response = requests.post('http://localhost:default_port/deepseek', json={'question': question})
        result = response.json()

    return JSONResponse(content=result)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        response = requests.post('http://localhost:default_port/deepseek', json={'question': data})
        result = response.json()
        await websocket.send_json(result)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)