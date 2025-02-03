import requests
import json
import mimetypes
import os
import fitz  # PyMuPDF for PDF
import pandas as pd  # For CSV
import pytesseract  # For OCR
from PIL import Image  # For image handling
from docx import Document  # For DOCX
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import faiss
import numpy as np

# API endpoint
url = "http://localhost:11434/api/generate"

def categorize_file(file_path):
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
    category = categorize_file(file_path)
    
    if category == "image":
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)
    elif category == "pdf":
        text = ""
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text
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
        return None

def create_faiss_index(documents):
    vectorizer = TfidfVectorizer(stop_words='english')
    vectors = vectorizer.fit_transform(documents).toarray()
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(np.array(vectors, dtype=np.float32))
    return index, vectorizer

def retrieve_relevant_content(index, vectorizer, query, documents, top_k=3):
    query_vector = vectorizer.transform([query]).toarray().astype(np.float32)
    distances, indices = index.search(query_vector, top_k)
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
            documents = file_content.split(". ")  # Simple sentence segmentation
            index, vectorizer = create_faiss_index(documents)
            relevant_content = retrieve_relevant_content(index, vectorizer, prompt, documents)

            data["prompt"] += f"\n\nAnswer the following prompt based on the provided attachment.\nAttachment Type: {category}. Relevant Content:\n{relevant_content}"
        elif category == "image":
            data["prompt"] += f"\n\nAttachment Type: {category}. Content:\n{file_content[:500]}"

    response = requests.post(url, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json().get('response', 'No response content available.')
    else:
        return "Failed to get a response from the API"

# Example usage
if __name__ == "__main__":
    prompt = input("Enter your prompt: ")
    file_path = input("Enter the file path (or leave blank if none): ")
    file_path = file_path if file_path.strip() else None

    result = send_request(prompt, file_path)
    print(result)
