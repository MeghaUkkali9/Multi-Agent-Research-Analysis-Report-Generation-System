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

## How the Multi-Agent Part Works

1. **Create the analyst team.** One LLM call creates a few analyst personas —
   each with a different name and a different angle on the topic (example: one
   focused on tech, one on business impact). Right after this, the pipeline
   pauses so someone can look at the team and edit or approve it before any
   interviews (the expensive part) start.

2. **Each analyst interviews an expert, all at the same time.** Every analyst
   gets its own private interview. These run in parallel — they are separate
   conversations, not one shared chat. Inside one interview:
   - the analyst asks a question
   - the app searches the web for that question (Tavily)
   - the expert (same LLM, but a different role/prompt) answers using only what
     the search results say — nothing made up
   - this repeats for a few rounds (`max_num_turns`), or stops early if the
     analyst says "thank you, that's enough"

3. **Each analyst writes a short section** based on its own interview.

4. **Two separate checks run on that section, at the same time:**
   - an editor checks if the writing is specific and not generic filler
   - a fact-checker checks if every claim is actually backed by the search
     results, or if the writer invented something

   If either check fails, the section goes back to be rewritten, along with the
   feedback that explains what was wrong. This can repeat a couple of times
   (`MAX_SECTION_REVISIONS`), then it stops and keeps whatever version exists —
   so one strict check can't loop forever.

5. **Once every analyst has finished**, all the sections get combined into one
   report. A separate writer role does this combining, and it only sees the
   finished sections, not the raw interviews. That same step also writes its
   own intro and conclusion.

```
create_analyst
      |
human_feedback   <- pauses here for human review of the analyst team
      |
      +--> one interview per analyst, all in parallel
      |
      analyst asks question -> web search -> expert answers
      (repeat a few rounds, or stop early if analyst says thanks)
            |
      write_section
            |
      editor checks it  +  fact-checker checks it   <- both run together
            |
      not approved? -> rewrite with their feedback (up to a revision cap)
      approved (or cap hit) -> done with this section
      |
all sections combined into one report + intro + conclusion
      |
final report
```

**Why this is actually multi-agent and not just one big prompt:**

- Each analyst is a separate persona with its own goals, not one LLM answering
  everything the same way.
- Interviews run in parallel, each with its own state, no shared conversation.
- Inside one interview, the same LLM plays two roles that don't trust each other
  blindly — the analyst pushes for specific answers, the expert only answers from
  what was actually searched.
- Editor and fact-checker are separate roles, checking the writer's work from two
  different angles instead of one agent grading itself.
- The report writer never sees the raw interviews, only the finished sections.
- A human gets a checkpoint before the expensive part (all the interviews) runs.

