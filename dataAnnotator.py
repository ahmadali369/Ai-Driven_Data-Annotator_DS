import os
import json
import time
import requests
import fitz  # PyMuPDF for PDF text extraction
import pandas as pd
import re
from pathlib import Path
from openpyxl.utils.exceptions import IllegalCharacterError

# API Details
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
API_KEY = "YOUR_GEMINI_API_KEY"

# Annotation Categories
CATEGORIES = ["Deep Learning", "Computer Vision", "Reinforcement Learning", "NLP", "Optimization"]
OUTPUT_FILE = "annotated_papers.xlsx"

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file, handling errors gracefully."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text.strip()[:3000]  # Limit to 3000 characters for API constraints
    except (fitz.FileDataError, fitz.FzErrorFormat) as e:
        print(f"❌ Error reading {pdf_path}: {e}")
        return None

def classify_paper(title, text):
    """Classify a research paper based on extracted text."""
    prompt = f"""Classify the following research paper into one of the predefined categories: {', '.join(CATEGORIES)}.
    Title: {title}
    Content: {text}
    Provide only the category name as output."""
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    max_retries = 5
    delay = 5
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={API_KEY}",
                headers={"Content-Type": "application/json"},
                json=data
            )
            print(f"Response Status: {response.status_code} (Attempt {attempt + 1})")
            
            if response.status_code == 200:
                response_json = response.json()
                print("🔍 API Response:", json.dumps(response_json, indent=4))
                category = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                return category if category in CATEGORIES else "Uncategorized"
            elif response.status_code in (429, 503):
                print(f"⚠️ Rate limit! Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ Unexpected error: {response.text}")
                return "Uncategorized"
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return "Uncategorized"
    return "Uncategorized"

def remove_illegal_chars(text):
    """Remove illegal characters that cause IllegalCharacterError in openpyxl."""
    if isinstance(text, str):
        return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)
    return text

def safe_write_to_excel(text, category):
    """Appends extracted text and category to an Excel file while handling illegal characters."""
    text = remove_illegal_chars(text)
    category = remove_illegal_chars(category)
    new_data = pd.DataFrame([{"Text": text, "Category": category}])
    
    try:
        if not os.path.exists(OUTPUT_FILE):
            new_data.to_excel(OUTPUT_FILE, index=False)
        else:
            with pd.ExcelWriter(OUTPUT_FILE, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
                new_data.to_excel(writer, index=False, header=False, startrow=writer.sheets["Sheet1"].max_row)
    except IllegalCharacterError:
        print("⚠️ Skipping row due to illegal characters.")

def annotate_papers(data_folder):
    """Extracts text from PDFs, classifies them, and appends results to an Excel file."""
    for pdf_file in Path(data_folder).glob("*.pdf"):
        title = pdf_file.stem.replace("_", " ")
        text = extract_text_from_pdf(pdf_file)
        
        if not text:
            print(f"⚠️ Skipping {title}: No text found or unreadable PDF!")
            continue
        
        print(f"Classifying: {title}")
        category = classify_paper(title, text)
        print(f"Assigned Category: {category}")
        
        safe_write_to_excel(text, category)
    print(f"✅ Annotation completed. Results saved in {OUTPUT_FILE}")

# Run the script
annotate_papers("/content/drive/MyDrive/NeurIPS_2024")
