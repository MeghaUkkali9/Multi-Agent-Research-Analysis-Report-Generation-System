# Multi-Agent Research Analysis Report Generation System
**Live demo:** https://multi-agent-report-generator-nzv2.onrender.com/

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

## Deploy for Free (Render)

This repo includes a `render.yaml` blueprint, so deploying is mostly clicking
buttons rather than configuring anything by hand:

1. Push this repo to GitHub if it isn't already (`origin` is already set up).
2. Go to [render.com](https://render.com), sign up, and choose
   **New > Blueprint**, then point it at this repo. Render reads `render.yaml`
   and sets up the web service automatically.
3. When prompted, fill in the env vars it asks for: `OPENAI_API_KEY`,
   `GROQ_API_KEY`, `TAVILY_API_KEY` (required), `LANGCHAIN_API_KEY` (optional,
   for tracing). See `.env.example` for what each one is.
4. Once it's live, Render gives a URL like `your-app.onrender.com`. Go back
   into the service's env vars and set `ALLOWED_ORIGINS` to that URL, then
   redeploy.

**Be upfront about the free-tier limitations, don't oversell them:**
- The free instance spins down after inactivity — the first request after
  that can take 30-60 seconds to wake back up.
- The filesystem is not persistent. `users.db` (signups) and generated
  reports both reset whenever the service restarts or redeploys. Fine for a
  demo where someone signs up, generates a report, and downloads it in one
  sitting — not fine as durable storage. Say this plainly if asked, rather
  than let someone discover it by losing their account.

## Deploy to AWS (CI/CD with Terraform + GitHub Actions)

This is the "real" deployment path — Terraform provisions the AWS infra
(ECS Fargate, ALB, ECR, IAM), and a GitHub Actions workflow builds, pushes,
and deploys a new image on every push to `main`. Costs real money the whole
time it's running (~$25-30/month, mostly the load balancer) — there's no
free tier for this like Render. Destroy it when you're not demoing.

**One-time setup:**

1. Install [Terraform](https://developer.hashicorp.com/terraform/install) and
   the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
   locally, then `aws configure` with an IAM user that has enough permissions
   to create the resources below (`AdministratorAccess` is the simplest way
   to start; tighten it later once it's working).

2. Provision the infra:
   ```bash
   cd infra
   terraform init
   terraform apply
   ```
   Review the plan, type `yes`. This creates: an ECR repo, an ECS Fargate
   cluster/service/task definition, an Application Load Balancer, IAM roles,
   empty Secrets Manager containers for the API keys, and an IAM role that
   GitHub Actions can assume via OIDC (no AWS access keys stored in GitHub).

3. Note two outputs from the apply: `github_actions_role_arn` and `app_url`.

4. In the GitHub repo: **Settings > Secrets and variables > Actions >
   Secrets**, add a repository secret named `AWS_DEPLOY_ROLE_ARN` set to
   the `github_actions_role_arn` output. (It's not actually sensitive — the
   OIDC trust policy is what gates access, not the ARN itself — but it lives
   as a Secret here, and the workflow reads it as `secrets.AWS_DEPLOY_ROLE_ARN`
   to match.)

5. Fill in the real secret values (Terraform only created empty containers —
   real keys never touch a `.tf` file or Terraform state):
   ```bash
   aws secretsmanager put-secret-value --secret-id multi-agent-report-gen/OPENAI_API_KEY --secret-string "sk-..."
   aws secretsmanager put-secret-value --secret-id multi-agent-report-gen/GROQ_API_KEY --secret-string "gsk_..."
   aws secretsmanager put-secret-value --secret-id multi-agent-report-gen/TAVILY_API_KEY --secret-string "tvly-..."
   aws secretsmanager put-secret-value --secret-id multi-agent-report-gen/LANGCHAIN_API_KEY --secret-string "lsv2_..."
   ```
   All four need *some* value (even a placeholder for the LangSmith one) —
   ECS fails to start the task if a referenced secret has no value at all.

6. Push to `main`. GitHub Actions builds the image, pushes it to ECR, and
   deploys it to ECS. The service sits at 0 healthy tasks until this first
   run finishes — that's expected, not broken; the infra goes up before the
   app does.

7. Visit `app_url` once the workflow finishes.

**To stop paying for it:** `terraform destroy` in `infra/`. This removes
everything, including the ECR images and the Secrets Manager values — bring
it back with `terraform apply` + re-running step 5 + a push (or just
re-running the last successful GitHub Actions workflow).

**Be upfront about what this setup doesn't do:**
- No HTTPS — the ALB only serves plain HTTP. Adding TLS needs a real domain
  name and an ACM certificate, skipped here to keep scope focused on the
  CI/CD pipeline itself.
- No persistent storage — same limitation as the Render deploy, if anything
  more so: `users.db` and generated reports live on the Fargate task's local
  disk, which disappears on every redeploy or task restart. Durable storage
  would mean swapping SQLite for RDS and generated files for S3 — a real
  application change, not an infra one, and out of scope here.

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

