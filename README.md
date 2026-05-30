# Multi-Agent Research Analysis Report Generation System

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/MeghaUkkali9/Multi-Agent-Research-Analysis-Report-Generation-System.git
cd Multi-Agent-Research-Analysis-Report-Generation-System
```

---

### 2. Create Virtual Environment (using uv)

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
```

---

### 3. Install Dependencies

```bash
uv pip install -r requirements.txt
```

---

### 4. Install Project as Package 

```bash
pip install -e .
```

This enables imports like:

```python
from research_analysis_generation.utils.model_loader import ModelLoader
```

---

### 5. Set Environment Variables

Create a `.env` file in project root:

```env
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
```

---

### 6. Verify Configuration

Ensure config file exists:

```
src/research_analysis_generation/config/config.yml
```

---

## Run Test (Model Loader)

Run the module:

```bash
python -m research_analysis_generation.utils.model_loader
```

---

## Expected Output

* Embedding model loads successfully
* LLM responds to test prompt
* Logs show successful initialization

---

## Project Structure

```
src/
└── research_analysis_generation/
    ├── config/
    │   └── config.yml
    ├── utils/
    │   ├── model_loader.py
    │   ├── config_loader.py
    │   └── api_key_manager.py
    ├── logger/
    └── exception/
```

---

## Notes

* Uses `src/` layout (best practice for Python packaging)
* Requires `pip install -e .` for correct imports
* Avoid running files directly via absolute paths

## Run Application
Get into virtual environment:
```
source .venv/bin/activate
```

```
uvicorn research_analysis_generation.api.main:app --reload
```

