import requests
import json
import mimetypes
import os

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
    else:
        return "unknown"

def process_file(file_path):
    category = categorize_file(file_path)
    
    if category == "image":
        with open(file_path, "rb") as f:
            return f.read().hex()  # Sending as hex string
    elif category in ["pdf", "csv", "text"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return None

def send_request(prompt, file_path=None):
    data = {
        "model": "deepseek-r1:1.5b",
        "prompt": prompt,
        "stream": False
    }
    
    if file_path:
        file_content = process_file(file_path)
        category = categorize_file(file_path)
        
        if file_content:
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
