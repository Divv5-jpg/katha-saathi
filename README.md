# Katha Saathi

A Streamlit story companion for children, using Sarvam AI for chat and optional speech-to-text/text-to-speech. The app keeps conversation state and playful badges in the active Streamlit session; it does not create persistent child profiles.

## Run locally

Requires Python 3.11 or later.

```powershell
python -m pip install -r requirements.txt
```

Set `SARVAM_API_KEY` in the root `.env` file (already excluded by `.gitignore`) or as an environment variable. Do not commit the key. Start the app:

```powershell
streamlit run app.py
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Streamlit Community Cloud

Deploy this repository and configure `SARVAM_API_KEY` in the app's **Settings → Secrets**. The app reads the secret server-side. Never put the key in source code or client-side settings.

## Story source and review

`data/panchatantra_stories.json` contains exactly five provisional, original retellings. No source document was supplied, so they are **not verified against a particular Panchatantra edition**. Before presenting them as source-verified, replace or review each story using a selected source and update `source_name`, `source_reference`, retelling, and `content_review_status`. The story library is local source material; the model is instructed not to invent or rewrite core events.

## Safety and privacy

The app is designed as a gentle companion, not a counsellor or character grader. It provides a prominent private-session explanation, avoids asking for identifying details, and uses safety-specific instructions for concerning messages. Children should use it with an appropriate trusted adult. Sarvam receives submitted messages to generate answers; avoid sharing highly personal information.
