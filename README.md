# ⚖️ LexIntel

**LexIntel** is an AI-powered litigation intelligence system designed to transform **unstructured legal documents into structured, actionable case events**.

Legal documents such as complaints, witness statements, and filings contain dense narratives that are difficult to analyze systematically. LexIntel extracts factual events from these narratives and converts them into structured data that can power advanced legal analysis.

This enables downstream capabilities such as:

* Timeline reconstruction of legal cases
* Detection of contradictions across documents
* Identification of weak or inconsistent claims
* Automated litigation intelligence

---

# 🚀 Overview: Current Module (Document Processing & Event Extraction)

The current repository implements the **Document Processing and Event Extraction pipeline**.

This module converts raw legal documents into a structured schema of events that can be used for higher-level legal reasoning.

## Pipeline Flow

1. **Legal Document Input**
   Raw legal documents in **PDF or text format**.

2. **Text Extraction**
   Extracts text from documents using **PDF parsing and OCR**.

3. **Section Detection**
   Identifies relevant legal sections within the document.

4. **Named Entity Recognition (NER)**
   Detects important entities such as:

   * People
   * Organizations
   * Locations
   * Dates

5. **LLM Event Extraction**
   Uses **Llama 3.1 via Groq API** to extract structured legal events from narrative text.

6. **Structured Event Output**
   Events are normalized into a consistent JSON schema.

---

# 📊 Data Schema

Each extracted event follows the structure below.

| Field           | Description                                |
| --------------- | ------------------------------------------ |
| actor           | Individual or entity performing the action |
| action          | Event or behavior described                |
| time            | When the event occurred (if specified)     |
| location        | Where the event occurred                   |
| source_document | Reference to the original file             |
| confidence      | Model confidence score                     |

### Example Output

Actor: Defendant
Action: Entered building
Time: 11:00 PM
Location: Belleville

Actor: Police
Action: Arrived at scene
Time: Unknown
Location: Agency building

Example JSON representation:

```json
{
  "actor": "Defendant",
  "action": "Entered building",
  "time": "11:00 PM",
  "location": "Belleville",
  "source_document": "case_123.pdf",
  "confidence": 0.92
}
```

---

# 🛠️ Tech Stack

### Programming Language

* Python

### NLP & Information Extraction

* spaCy (`en_core_web_sm`)

### LLM Inference

* Groq API
* Llama 3.1

### Document Processing

* pdfplumber

### OCR

* Tesseract OCR

---

# ⚙️ Installation & Setup

## Prerequisites

Install **Tesseract OCR** on your system:

https://tesseract-ocr.github.io/tessdoc/Installation.html

Verify installation:

```bash
tesseract --version
```

---

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/LexIntel.git
cd LexIntel
```

---

## 2️⃣ Install Dependencies

```bash
pip install -e .
```

---

## 3️⃣ Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

---

## 4️⃣ Configure Dataset

The pipeline supports the **Caselaw Access Project dataset**.

Place the dataset file here:

```
dataset/text.data.jsonl
```

Large datasets are ignored by git using `.gitignore`.

---

## 5️⃣ Run the Pipeline

```bash
python backend/test_pipeline.py
```

The pipeline will:

1. Process legal documents
2. Extract entities and events
3. Generate structured outputs

---

# 🗺️ Project Roadmap

The **Document Processing & Event Extraction module** is complete.

Future development will expand the system into a full litigation intelligence platform.

### Planned Features

**Timeline Construction**

* Chronological reconstruction of case events

**Contradiction Detection**

* Detect inconsistencies across multiple documents

**Case Weakness Analysis**

* Identify factual weaknesses in legal arguments

**AI Hearing Simulation**

* Interactive environment to simulate court questioning

---

# 📄 License

This project is currently under development and intended for **research and educational use**.

License details will be finalized in future releases.
