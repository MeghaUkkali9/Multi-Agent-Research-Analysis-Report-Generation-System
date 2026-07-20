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

## Multi-Agent Architecture

The report pipeline is a LangGraph state machine with two nested graphs: an outer
**report graph** and an inner **interview graph**, run once per analyst.

```
create_analyst
      |
human_feedback  (interrupt — human can edit/reject the analyst team)
      |
      +--> Send() fans out one parallel "conduct_interview" run per analyst
      |
conduct_interview (subgraph, one instance per analyst, running concurrently)
      |
      +--> generate_question   (analyst persona asks the expert a question)
      +--> search_web          (Tavily query grounds the next answer)
      +--> generate_answer     (expert answers using only retrieved context)
      +--> route_messages      (loop back to generate_question, up to
      |                         max_num_turns, unless the analyst has said
      |                         "Thank you so much for your help!")
      +--> save_transcript
      +--> write_section       (one report section per analyst)
      +--> review_section      (editor agent grades the section; if rejected,
      |                         loops back to write_section with feedback +
      |                         the previous draft, up to MAX_SECTION_REVISIONS)
      |
write_report / write_introduction / write_conclusion   (run in parallel
      |                                                  over all sections)
      v
finalize_report
```

Why this counts as "multi-agent" rather than a single prompt chain:

- **Distinct personas, not one LLM call**: `create_analyst` generates N independent
  `Analyst` personas (name, role, affiliation, focus) via structured output. Each
  drives its own interview with a different system prompt built from `analyst.persona`.
- **Parallel, isolated execution**: `initiate_all_interviews` uses LangGraph's `Send`
  API to fan out one `conduct_interview` subgraph invocation per analyst — these run
  concurrently with their own state (`InterviewState`), not a shared conversation.
- **Two-role simulation inside each interview**: the same LLM plays both the
  `analyst` (asking, driving toward specific/non-obvious insights) and the `expert`
  (answering strictly from retrieved search context, citing sources) — a genuine
  multi-turn back-and-forth bounded by `max_num_turns`, not one question/one answer.
- **Tool-using agent**: `search_web` gives the expert role live grounding via Tavily
  before every answer, so answers are sourced rather than hallucinated.
- **Reflect-and-revise loop**: `review_section` is a fourth role — an editor agent
  that never sees the raw interview, only the finished draft — grading it against
  explicit criteria (specific insights, cited claims, structure, dedup'd sources)
  via structured output. A rejection routes back to `write_section` with the
  editor's feedback and the previous draft attached, so the rewrite is a genuine
  revision, not a fresh guess. Capped at `MAX_SECTION_REVISIONS` so a strict critic
  can't loop forever.
- **Map-reduce synthesis**: sections written independently per analyst are combined
  by a separate writer role (`write_report`) that has never seen the raw interviews —
  only the finished memos — then stitched with independently generated introduction
  and conclusion sections.
- **Human-in-the-loop checkpoint**: `human_feedback` is a LangGraph `interrupt_before`
  node — the graph pauses after analyst creation so a person can redirect the team
  before any interviews (and their API/token cost) run.

