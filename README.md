# Citation Tool — Verifier, Finder & Literature Generator

A two-tab tool that solves the academic citation hallucination problem.

## The Problem

AI tools like ChatGPT confidently generate fake academic references — 
real-looking titles, plausible authors, and DOIs that don't exist. 
Journal editors and researchers have no easy way to catch these.

## The Solution

**Tab 1 — Citation Verifier**
Paste any AI-generated bibliography. The tool checks every reference against 
CrossRef (the official DOI registry) and Semantic Scholar, flagging:
- ✅ Real — DOI verified and details match
- ⚠️ Details Mismatch — DOI exists but title or authors don't match
- ⚠️ Unverifiable — No DOI (books, preprints, pre-2000 papers)
- ❌ Hallucinated — DOI doesn't exist anywhere

**Tab 2 — Citation Finder**
Search for real verified papers by topic. Filter by field of study, 
year range, citation count, and author. Results ranked by a combined 
score of relevance, citations, and recency. Every result includes 
a verified DOI and abstract.

**Tab 3 — Literature Review Generator**
Describe your research topic and the tool finds real verified papers, 
then uses GPT-4o to write a grounded literature review paragraph 
citing only those verified sources. Zero hallucination risk — 
every citation traces back to a CrossRef-verified paper.

## Live Demo

[Launch the app](https://citation-tool-ps8wt8a668uyaslb7ch2xy.streamlit.app)

## Tech Stack

- Python + Streamlit
- OpenAI GPT-4o — extracts structured references from any bibliography format
- CrossRef API — official DOI verification
- OpenAlex API — paper search and discovery
- Semantic Scholar API — title verification fallback

## Why This Matters

Tested on ChatGPT-generated citations — flagged 5 out of 10 as 
either hallucinated or containing wrong details. 
One tab fixes the problem. The other prevents it.

## Run Locally

```bash
git clone https://github.com/Bubbletrip/citation-tool.git
cd citation-tool
pip install -r requirements.txt
streamlit run app.py
```

Add your OpenAI API key to a `.env` file:

## Built By

Tarun Shetty — IIT Bombay ePGD in Artificial Intelligence and Data Science 2025-2026