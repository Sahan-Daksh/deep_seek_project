import requests
import json
import os
import fitz  # PyMuPDF for PDF handling
import pandas as pd  # CSV and XLSX handling
import pytesseract  # OCR for images and scanned PDFs
from PIL import Image  # Image processing
from docx import Document  # DOCX file handling
from pptx import Presentation  # PPTX file handling
from openpyxl import load_workbook  # XLSX handling
import faiss
import numpy as np
import logging
import nltk
from sentence_transformers import SentenceTransformer
from pdf2image import convert_from_path  # Convert PDF pages to images
import comtypes.client  # Convert PPTX/DOCX/XLSX to PDF (requires MS Office)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logging.info("Downloading NLTK 'punkt' tokenizer...")
    nltk.download('punkt')

# Set Tesseract path (update this if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# API endpoint
url = "http://localhost:11434/api/generate"

def categorize_file(file_path):
    """Determine the file type based on extension."""
    if not file_path:
        return "unknown"
    extension = os.path.splitext(file_path)[1].lower()
    if extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
        return "image"
    elif extension == ".pdf":
        return "pdf"
    elif extension == ".csv":
        return "csv"
    elif extension == ".xlsx":
        return "xlsx"
    elif extension == ".pptx":
        return "pptx"
    elif extension == ".docx":
        return "docx"
    elif extension in [".txt", ".md"]:
        return "text"
    else:
        return "unknown"

# ... (keep all your existing file processing functions) ...

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive the prompt and file path from the client
            data = await websocket.receive_json()
            prompt = data.get("prompt")
            file_path = data.get("file_path")

            if prompt.lower() == "exit":
                break

            # Process the request
            result = send_request(prompt, file_path)
            
            # Send the response back to the client
            await websocket.send_json({
                "response": result,
                "timestamp": str(datetime.datetime.now())
            })

            # Get feedback from the user
            feedback_data = await websocket.receive_json()
            if feedback_data.get("helpful") == "no":
                clarification = feedback_data.get("clarification")
                if clarification:
                    result = send_request(clarification, file_path)
                    await websocket.send_json({
                        "response": result,
                        "timestamp": str(datetime.datetime.now())
                    })

    except WebSocketDisconnect:
        logging.info("WebSocket connection closed")

def send_request(prompt, file_path=None):
    """Send request to API with relevant file content."""
    data = {"model": "deepseek-r1:1.5b", "prompt": prompt, "stream": False}

    if file_path:
        file_content = process_file(file_path)
        category = categorize_file(file_path)

        if file_content and category in ["pdf", "csv", "text", "docx", "pptx", "xlsx"]:
            documents = chunk_document(file_content)
            index, model = create_faiss_index(documents)
            relevant_content = retrieve_relevant_content(index, model, prompt, documents)

            data["prompt"] += f"\n\nAnswer the following prompt based on the provided attachment.\nAttachment Type: {category}. Relevant Content:\n{relevant_content}"
        elif category == "image":
            data["prompt"] += f"\n\nExtracted Text from Image:\n{file_content}"
        else:
            logging.warning(f"Cannot process file: {file_path}")
            return "Unsupported file type."

    try:
        response = requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return response.json().get('response', 'No response available.')
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return "Failed to communicate with the API."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)