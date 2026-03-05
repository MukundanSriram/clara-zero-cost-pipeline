# Sample Dataset

This folder contains **sample transcripts** used to run the Clara zero-cost pipeline (demo → v1, onboarding → v2 + changelog).

## Sample account: Ben's Electric

| Item | Source |
|------|--------|
| **Customer / Account** | Ben's Electric / Ben's Electric Solutions |
| **Product** | Clara Answering Agent |
| **Demo call recording** | [Fireflies.ai – Clara Product Demo](https://app.fireflies.ai/view/01KEFDQJ7E0EZR9WDFBWK774D9) |
| **Onboarding call recording** | [Google Drive – Ben's Electric Solutions](https://drive.google.com/drive/folders/1k-sUTmD1OZsbDWEq0avQwdwTk-JDG-N1?usp=drive_link) (e.g. "2026-01-14 11.04.17 Clara Product's Personal Meeting Room") |

The transcript files in this repo are **derived from the provided demo and onboarding call summaries** (Ben's Electric Solutions / Ben Penoyer, Clara Answering Agent). They are written in a form the pipeline can parse to produce account memos and agent specs. To use verbatim transcripts instead:

1. Export or copy the transcript from Fireflies for the demo call and save as `dataset/demo/bens_electric_demo_1.txt` (or add more files like `bens_electric_demo_2.txt`).
2. Download the onboarding recording from Google Drive, transcribe it (e.g. with a free tool like Whisper locally), and save as `dataset/onboarding/bens_electric_onboarding_1.txt`.

File naming convention: `<account_id>_demo_<n>.txt` and `<account_id>_onboarding_<n>.txt`. The pipeline derives `account_id` from the filename prefix (e.g. `bens_electric`).

## Folder layout

- `demo/` – Demo call transcripts (one or more `.txt` per account).
- `onboarding/` – Onboarding call transcripts (one or more `.txt` per account).

Replace or add `.txt` files here, then run the demo and onboarding pipelines (via terminal or n8n) to regenerate `outputs/accounts/<account_id>/v1` and `v2` and `changelog/`.
