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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def convert_to_pdf(file_path):
    """Convert PPTX, DOCX, or XLSX files to PDF using comtypes (requires Microsoft Office)."""
    try:
        output_pdf = os.path.splitext(file_path)[0] + ".pdf"
        file_type = categorize_file(file_path)

        if file_type == "pptx":
            app = comtypes.client.CreateObject("Powerpoint.Application")
            app.Visible = 1
            presentation = app.Presentations.Open(file_path, WithWindow=False)
            presentation.SaveAs(output_pdf, 32)  # 32 = PDF format
            presentation.Close()
            app.Quit()
        
        elif file_type == "docx":
            app = comtypes.client.CreateObject("Word.Application")
            app.Visible = 0
            doc = app.Documents.Open(file_path)
            doc.SaveAs(output_pdf, FileFormat=17)  # 17 = PDF format
            doc.Close()
            app.Quit()
        
        elif file_type == "xlsx":
            app = comtypes.client.CreateObject("Excel.Application")
            app.Visible = 0
            workbook = app.Workbooks.Open(file_path)
            workbook.ExportAsFixedFormat(0, output_pdf)  # 0 = PDF format
            workbook.Close()
            app.Quit()
        
        return output_pdf
    except Exception as e:
        logging.error(f"Error converting {file_path} to PDF: {e}")
        return None

def process_file(file_path):
    """Process a file based on its type."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None
    
    category = categorize_file(file_path)
    
    if category == "image":
        return process_image(file_path)
    elif category == "pdf":
        return process_pdf(file_path)
    elif category == "csv":
        df = pd.read_csv(file_path)
        return df.to_string()
    elif category == "xlsx":
        df = pd.read_excel(file_path)
        return df.to_string()
    elif category in ["pptx", "docx"]:
        pdf_path = convert_to_pdf(file_path)
        return process_pdf(pdf_path) if pdf_path else None
    elif category == "text":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        logging.warning(f"Unsupported file type: {file_path}")
        return None

def process_image(file_path):
    """Extract text from an image using OCR."""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip() or "No readable text found in the image."
    except Exception as e:
        logging.error(f"Error processing image {file_path}: {e}")
        return "Image processing failed."

def process_pdf(file_path):
    """Extract text from a PDF."""
    text = ""
    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        if not text.strip():
            logging.info("No text extracted from PDF. Attempting OCR...")
            images = convert_from_path(file_path)
            text = " ".join([pytesseract.image_to_string(img) for img in images])
        return text
    except Exception as e:
        logging.error(f"Error processing PDF {file_path}: {e}")
        return None

def chunk_document(text):
    """Chunk text into sentences for efficient processing."""
    try:
        return nltk.sent_tokenize(text)
    except Exception as e:
        logging.error(f"Error chunking document: {e}")
        return [text]

def create_faiss_index(documents):
    """Create a FAISS index for fast retrieval."""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    vectors = model.encode(documents)
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(np.array(vectors, dtype=np.float32))
    return index, model

def retrieve_relevant_content(index, model, query, documents, top_k=3):
    """Retrieve the most relevant content from documents."""
    query_vector = model.encode([query])
    distances, indices = index.search(np.array(query_vector, dtype=np.float32), top_k)
    return "\n".join([documents[i] for i in indices[0]])

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

            data["prompt"] += f"\n\nBased on the file:\n{relevant_content}"
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

def interactive_chat():
    """Interactive chat with file support."""
    while True:
        prompt = input("Enter your prompt (or type 'exit' to quit): ")
        if prompt.lower() == "exit":
            break
        file_path = input("Enter file path (or leave blank): ").strip('"') or None
        result = send_request(prompt, file_path)
        print(result)

if __name__ == "__main__":
    interactive_chat()