## Clara Zero-Cost Automation Pipeline

This repository implements a **zero-cost, fully local and reproducible** pipeline to convert:

- **Demo call transcripts** into:
  - Structured **Account Memo JSON** (`v1`)
  - **Retell Agent Draft Spec** (`v1`)
  - A **tracking item** (Asana if configured, or a local tasks log)
- **Onboarding call transcripts** into:
  - Updated **Account Memo JSON** (`v2`)
  - Updated **Retell Agent Draft Spec** (`v2`)
  - A **per-account changelog** explaining what changed and why

Everything runs using **free tools only** (no paid LLM/API usage is required).

---

## Architecture Overview

- **Language**: Python 3.10+ (stdlib only, no paid APIs)
- **Orchestrator**: `n8n` (self-hosted, local, via Docker)
- **Storage**: Local JSON files under `outputs/`
- **Task Tracker**:
  - Preferred: **Asana** free tier via API (optional, configurable)
  - Fallback: Local JSON log under `outputs/tasks/`
- **Transcripts**: Plain text files (if you only have audio, transcribe first using a free local tool like Whisper)

### Data Flow (High Level)

1. **Demo Pipeline (Pipeline A)**
   - Input: demo transcript file
   - `scripts/extract_account_memo.py` → `outputs/accounts/<account_id>/v1/memo.json`
   - `scripts/generate_agent_spec.py` → `outputs/accounts/<account_id>/v1/agent_spec.json`
   - `scripts/create_task_item.py` → Asana task (or local task log)

2. **Onboarding Pipeline (Pipeline B)**
   - Input: onboarding transcript file
   - `scripts/extract_account_memo.py` → **patch memo** based on onboarding
   - `scripts/update_from_onboarding.py`:
     - reads existing `v1` memo + spec
     - computes updated `v2` memo
     - regenerates `v2` agent spec
     - writes per-account changelog under `changelog/<account_id>.md` and `.json`

3. **Orchestration (n8n)**
   - `workflows/demo_pipeline.json`: batch process all demo transcripts
   - `workflows/onboarding_pipeline.json`: batch process all onboarding transcripts and update to `v2`

---

## Repository Structure

- `scripts/`
  - `extract_account_memo.py` – parses a transcript into the Account Memo JSON
  - `generate_agent_spec.py` – generates a Retell Agent Draft Spec from a memo
  - `process_demo_calls.py` – batch runs Pipeline A over demo transcripts
  - `process_onboarding_calls.py` – batch runs Pipeline B over onboarding transcripts
  - `create_task_item.py` – optional Asana (or local) task creation per account
- `workflows/`
  - `demo_pipeline.json` – n8n workflow export for Pipeline A
  - `onboarding_pipeline.json` – n8n workflow export for Pipeline B
- `outputs/`
  - `accounts/<account_id>/v1/` – `memo.json`, `agent_spec.json`
  - `accounts/<account_id>/v2/` – `memo.json`, `agent_spec.json`
  - `tasks/` – local task log if Asana not configured
- `changelog/`
  - `<account_id>.md` – human-readable changelog
  - `<account_id>.json` – structured diff

You can safely delete `outputs/` and `changelog/` content and regenerate them by rerunning the pipelines (idempotent behavior).

---

## Account Memo JSON Schema

Each account memo produced by the pipeline has at least these fields:

```json
{
  "account_id": "acme_fire",
  "company_name": "Acme Fire & Safety",
  "business_hours": {
    "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "start": "08:00",
    "end": "17:00",
    "timezone": "America/Los_Angeles"
  },
  "office_address": "123 Main St, Springfield, OR 97477",
  "services_supported": ["sprinkler repair", "alarm monitoring"],
  "emergency_definition": ["active water flow", "fire alarm going off"],
  "emergency_routing_rules": {
    "primary": ["on_call_technician"],
    "fallback": ["branch_manager"],
    "notes": "If no pickup in 2 minutes, call branch_manager."
  },
  "non_emergency_routing_rules": {
    "primary": ["front_desk"],
    "fallback": ["voicemail_box"],
    "notes": ""
  },
  "call_transfer_rules": {
    "timeout_seconds": 30,
    "max_retries": 2,
    "failure_message": "I’m unable to reach the on-call team right now, but I will log your details and someone will call you back as soon as possible."
  },
  "integration_constraints": [
    "Never create sprinkler jobs in ServiceTrade without a work order from dispatch."
  ],
  "after_hours_flow_summary": "",
  "office_hours_flow_summary": "",
  "questions_or_unknowns": [
    "After-hours flow not clearly described in transcript."
  ],
  "notes": "Short free-text notes about the account."
}
```

If a detail is missing, the extractor leaves it empty or adds an entry under `questions_or_unknowns`. It **does not fabricate** values.

---

## Retell Agent Draft Spec

For each account, we generate a **Retell-compatible agent spec** (JSON) with:

- `agent_name`
- `voice_style`
- `system_prompt` (full call-handling instructions)
- `variables` (timezone, business hours, address, emergency routing, etc.)
- `call_transfer_protocol`
- `fallback_protocol`
- `version` (`v1` or `v2`)

The spec is **not** pushed to Retell via API (to keep everything zero-cost and portable), but you can:

1. Create an agent manually in the Retell dashboard.
2. Copy-paste the `system_prompt` and key settings from the generated JSON.

See `docs/RETELL_SETUP.md` (to be created) for exact Retell UI mapping.

---

## Running Locally

### 1. Prerequisites

- Python **3.10+**
- Docker + Docker Compose (for `n8n`)
- (Optional) Asana account with a Personal Access Token (free tier)

### 2. Dataset Layout

Place your transcripts like this:

- `dataset/demo/` – 5 demo call transcripts
- `dataset/onboarding/` – 5 onboarding call transcripts

File naming convention (configurable in scripts):

- Demo: `<account_id>_demo_<N>.txt`
- Onboarding: `<account_id>_onboarding_<N>.txt`

The **`<account_id>` prefix must match** between demo and onboarding files (e.g. `bens_electric_demo_1.txt` and `bens_electric_onboarding_1.txt`).

**Sample data (Ben's Electric)**  
This repo includes sample transcripts for **Ben's Electric** / **Ben's Electric Solutions** (Clara Answering Agent):

- Demo call source: [Fireflies.ai](https://app.fireflies.ai/view/01KEFDQJ7E0EZR9WDFBWK774D9)
- Onboarding call source: [Google Drive](https://drive.google.com/drive/folders/1k-sUTmD1OZsbDWEq0avQwdwTk-JDG-N1?usp=drive_link)

See `dataset/README.md` for details and how to replace with real transcripts.

### 3. Python Pipelines (without n8n)

Run **Pipeline A (demo → v1)**:

```bash
python3 scripts/process_demo_calls.py \
  --demo-dir dataset/demo \
  --outputs-dir outputs/accounts
```

Run **Pipeline B (onboarding → v2 + changelog)**:

```bash
python3 scripts/process_onboarding_calls.py \
  --onboarding-dir dataset/onboarding \
  --outputs-dir outputs/accounts \
  --changelog-dir changelog
```

You can safely rerun these commands; they update the same `v1`/`v2` folders and overwrite previous derived files in a controlled way.

---

## n8n Setup (Required Orchestrator)

### 1. Run n8n Locally

Create a `docker-compose.yml` (example in this repo, or follow n8n docs), then:

```bash
docker compose up -d
```

Open n8n at `http://localhost:5678` and complete initial setup.

### 2. Import Workflows

1. In n8n UI, go to **Workflows → Import**.
2. Import `workflows/demo_pipeline.json`.
3. Import `workflows/onboarding_pipeline.json`.
4. Set environment variables in the n8n instance if needed:
   - `DATASET_DEMO_DIR` (e.g. `dataset/demo`)
   - `DATASET_ONBOARDING_DIR` (e.g. `dataset/onboarding`)
   - `OUTPUTS_DIR` (e.g. `outputs/accounts`)
   - `CHANGELOG_DIR` (e.g. `changelog`)
   - Optional Asana:
     - `ASANA_ACCESS_TOKEN`
     - `ASANA_PROJECT_ID`

The workflows primarily invoke the Python scripts via an **Execute Command** node, so behavior is identical to running the commands manually:

- Demo workflow command:

  ```bash
  python3 scripts/process_demo_calls.py --demo-dir "{{ $env.DATASET_DEMO_DIR || 'dataset/demo' }}" --outputs-dir "{{ $env.OUTPUTS_DIR || 'outputs/accounts' }}"
  ```

- Onboarding workflow command:

  ```bash
  python3 scripts/process_onboarding_calls.py --onboarding-dir "{{ $env.DATASET_ONBOARDING_DIR || 'dataset/onboarding' }}" --outputs-dir "{{ $env.OUTPUTS_DIR || 'outputs/accounts' }}" --changelog-dir "{{ $env.CHANGELOG_DIR || 'changelog' }}"
  ```

---

## UI Dashboard (Required for this Setup)

This repo includes a lightweight **Streamlit** dashboard to browse accounts, compare `v1` and `v2` memos, inspect agent specs, and view changelogs.

### 1. Install UI dependency

From the project root:

```bash
python3 -m pip install -r requirements.txt
```

### 2. Run the dashboard

Make sure you have already run the pipelines at least once (so `outputs/accounts/...` and `changelog/` exist), then:

```bash
streamlit run ui/app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`) in your browser. You can:

- Select an `account_id` from the sidebar.
- See `v1` vs `v2` memos and agent specs side-by-side.
- Scroll down to see the markdown changelog.

---

## Task Tracking (Asana or Local)

- If `ASANA_ACCESS_TOKEN` and `ASANA_PROJECT_ID` are set:
  - `scripts/create_task_item.py` will create one task per `account_id` in Asana.
- If they are **not set**:
  - The script falls back to appending a JSON entry to `outputs/tasks/local_tasks.json`, which you can open in any viewer or import into your preferred tool.

This keeps the solution **zero-cost** and fully reproducible without requiring external SaaS.

---

## Retell Setup (Manual Import)

Because we avoid paid or non-free programmatic access:

1. Create a Retell account on their free tier.
2. In the Retell dashboard, create a new agent.
3. From `outputs/accounts/<account_id>/v1/agent_spec.json`:
   - Copy `agent_name`, `voice_style`, and especially `system_prompt`.
   - Map `variables` and routing rules to the appropriate Retell settings.
4. After onboarding updates (v2), you can either:
   - Update the same agent with the new `system_prompt`, or
   - Create a new versioned agent and note the linkage.

Exact field mappings and suggestions will be documented in `docs/RETELL_SETUP.md`.

---

## Known Limitations

- The default extractor is **rule-based** and conservative; it prefers to leave fields empty and surface `questions_or_unknowns` instead of guessing.
- No heavy local LLM is required; however, you may optionally plug in an open-source LLM (e.g. via Ollama) behind the same extraction interface.
- Audio-only inputs are not handled directly; you must transcribe them first using a free local tool like Whisper and then drop the transcripts into `dataset/`.

---

## What I Would Improve for Production

- Swap the rule-based extractor with a robust local LLM (e.g. fine-tuned or prompt-engineered) for higher recall and precision.
- Add a minimal UI (e.g. Streamlit) to:
  - upload transcripts,
  - preview memos and agent specs,
  - visualize diffs between `v1` and `v2`.
- Harden error handling and logging (structured logs, retry policies, basic observability).
- Add automated unit tests around extraction and diff logic to guard against regressions.

