import requests
import json
import os
import fitz  # PyMuPDF for PDF
import pandas as pd  # For CSV
import pytesseract  # For OCR
from PIL import Image  # For image handling
from docx import Document  # For DOCX
import faiss
import numpy as np
import logging
import nltk
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Ensure NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logging.info("Downloading NLTK 'punkt' tokenizer...")
    nltk.download('punkt')

# API endpoint
url = "http://localhost:11434/api/generate"

def categorize_file(file_path):
    if not file_path:
        return "unknown"
    extension = os.path.splitext(file_path)[1].lower()
    if extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
        return "image"
    elif extension == ".pdf":
        return "pdf"
    elif extension == ".csv":
        return "csv"
    elif extension in [".txt", ".md"]:
        return "text"
    elif extension == ".docx":
        return "docx"
    else:
        return "unknown"

def process_file(file_path):
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None
    try:
        category = categorize_file(file_path)
        if category == "image":
            image = Image.open(file_path)
            return pytesseract.image_to_string(image)
        elif category == "pdf":
            return process_pdf(file_path)
        elif category == "csv":
            df = pd.read_csv(file_path)
            return df.to_string()
        elif category == "text":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif category == "docx":
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            logging.warning(f"Unsupported file type: {file_path}")
            return None
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return None

def process_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        if not text.strip():  # If no text is extracted, assume it's a scanned PDF
            logging.info("No text extracted from PDF. Attempting OCR...")
            images = []
            with fitz.open(file_path) as pdf:
                for page_num, page in enumerate(pdf):
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    images.append(img)
            text = " ".join([pytesseract.image_to_string(img) for img in images])
        return text
    except Exception as e:
        logging.error(f"Error processing PDF {file_path}: {e}")
        return None

def chunk_document(text):
    try:
        sentences = nltk.sent_tokenize(text)
        return sentences
    except Exception as e:
        logging.error(f"Error chunking document: {e}")
        return [text]  # Fallback to treating the entire text as one chunk

def create_faiss_index(documents):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    vectors = model.encode(documents)
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(np.array(vectors, dtype=np.float32))
    return index, model

def retrieve_relevant_content(index, model, query, documents, top_k=3):
    query_vector = model.encode([query])
    distances, indices = index.search(np.array(query_vector, dtype=np.float32), top_k)
    relevant_content = "\n".join([documents[i] for i in indices[0]])
    return relevant_content

def send_request(prompt, file_path=None):
    data = {
        "model": "deepseek-r1:1.5b",
        "prompt": prompt,
        "stream": False
    }
    
    if file_path:
        file_content = process_file(file_path)
        category = categorize_file(file_path)

        if file_content and category in ["pdf", "csv", "text", "docx"]:
            documents = chunk_document(file_content)
            index, model = create_faiss_index(documents)
            relevant_content = retrieve_relevant_content(index, model, prompt, documents)

            data["prompt"] += f"\n\nAnswer the following prompt based on the provided attachment.\nAttachment Type: {category}. Relevant Content:\n{relevant_content}"
        elif category == "image":
            data["prompt"] += f"\n\nAttachment Type: {category}. Content:\n{file_content[:500]}"
        else:
            logging.warning(f"Cannot process file: {file_path}")
            return "The file type is unsupported or the file could not be processed."

    try:
        response = requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return response.json().get('response', 'No response content available.')
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return "Failed to get a response from the API"

def interactive_chat():
    while True:
        prompt = input("Enter your prompt (or type 'exit' to quit): ")
        if prompt.lower() == "exit":
            break
        file_path = input("Enter the file path (or leave blank if none): ").strip('"')
        file_path = file_path if file_path.strip() else None

        result = send_request(prompt, file_path)
        print(result)

        # Ask for feedback
        feedback = input("Was this response helpful? (yes/no): ")
        if feedback.lower() == "no":
            clarification = input("What additional information do you need? ")
            result = send_request(clarification, file_path)
            print(result)

if __name__ == "__main__":
    interactive_chat()