import streamlit as st
import requests
import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Citation Tool", layout="wide")

tab1, tab2 = st.tabs(["📋 Citation Verifier", "🔍 Citation Finder"])

# ─────────────────────────────────────────
# TAB 1 — CITATION VERIFIER
# ─────────────────────────────────────────
with tab1:
    st.title("📋 Citation Verifier")
    st.write("Paste your AI-generated bibliography below. We'll check every reference for you.")

    st.info("""
    **How verification works:**
    - ✅ REAL — DOI confirmed by CrossRef (official DOI registry) and details match
    - ⚠️ DETAILS MISMATCH — DOI is real but title or authors don't match — possible hallucination
    - ⚠️ UNVERIFIABLE — No DOI found. Common for books and pre-2000 works. Manual check recommended
    - ❌ HALLUCINATED — DOI not found in CrossRef registry or paper not found anywhere
    
    **Note:** This tool is optimised for journal articles with DOIs. 
    Books and older works without DOIs will show as Unverifiable — this is expected, not an error. 
    Always manually check Unverifiable results.
    """)

    bibliography = st.text_area("Paste your bibliography here", height=300)

    if st.button("Verify Citations"):
        if bibliography:
            with st.spinner("Extracting references using AI..."):

                prompt = f"""
                Extract all academic references from the following bibliography.
                For each reference return a JSON array where each item has:
                - title (string)
                - authors (string)
                - year (string)
                - doi (string or null if not present)
                
                Return ONLY the JSON array, nothing else.
                
                Bibliography:
                {bibliography}
                """

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                raw = response.choices[0].message.content
                clean = raw.replace("```json", "").replace("```", "").strip()
                references = json.loads(clean)

            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total = len(references)

            for i, ref in enumerate(references):
                title = ref.get("title", "Unknown title")
                authors = ref.get("authors", "Unknown authors")
                year = ref.get("year", "Unknown year")
                doi = ref.get("doi", None)

                short_title = title[:40] + "..." if len(title) > 40 else title
                status_text.text(f"Verifying {i+1} of {total}: {short_title}")

                if doi:
                    crossref = requests.get(f"https://api.crossref.org/works/{doi}")
                    time.sleep(0.2)

                    if crossref.status_code == 200:
                        cr_data = crossref.json().get("message", {})
                        cr_title = cr_data.get("title", [""])[0].lower().strip()
                        cr_authors = cr_data.get("author", [])
                        cr_author_names = " ".join([
                            a.get("family", "").lower()
                            for a in cr_authors[:2]
                        ])

                        title_match = cr_title and (
                            title.lower()[:30] in cr_title or
                            cr_title[:30] in title.lower()
                        )
                        author_match = any(
                            a.split()[-1].lower() in cr_author_names
                            for a in authors.split(",")[:2]
                        )

                        if title_match and author_match:
                            verdict = "✅ REAL"
                            detail = "DOI verified and details match"
                        elif title_match or author_match:
                            verdict = "⚠️ DETAILS MISMATCH"
                            detail = f"DOI exists but details differ — CrossRef title: '{cr_data.get('title', ['?'])[0][:60]}'"
                        else:
                            verdict = "⚠️ DETAILS MISMATCH"
                            detail = "DOI exists but title and authors don't match CrossRef record"
                    else:
                        verdict = "❌ HALLUCINATED"
                        detail = "DOI not found in CrossRef registry"
                else:
                    # Try Semantic Scholar first
                    search = requests.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search",
                        params={"query": title, "limit": 1, "fields": "title,year"}
                    )
                    time.sleep(0.2)
                    results_ss = search.json().get("data", [])

                    # Try arXiv as second source
                    arxiv_found = False
                    try:
                        arxiv_search = requests.get(
                            f"http://export.arxiv.org/api/query?search_query=ti:{title[:50]}&max_results=1",
                            timeout=5
                        )
                        if arxiv_search.status_code == 200 and title.lower()[:20] in arxiv_search.text.lower():
                            arxiv_found = True
                    except:
                        arxiv_found = False

                    if results_ss and results_ss[0]["title"].lower() == title.lower():
                        verdict = "⚠️ UNVERIFIABLE"
                        detail = "No DOI but title found in Semantic Scholar — likely real. DOIs weren't standard before 2000; manual check recommended."
                    elif arxiv_found:
                        verdict = "⚠️ UNVERIFIABLE"
                        detail = "No DOI but found on arXiv — likely real preprint. ArXiv papers use arXiv IDs not DOIs; manual check recommended."
                    else:
                        # Determine likely reason
                        if year and int(year) < 2000:
                            detail = "No DOI — pre-2000 paper. DOIs weren't standard before 2000. Verify manually — this doesn't mean it's fake."
                        else:
                            detail = "No DOI found — likely a conference paper, arXiv preprint, or book. Verify manually via Google Scholar."
                        verdict = "⚠️ UNVERIFIABLE"

                

                results.append({
                    "short_title": short_title,
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "doi": doi,
                    "verdict": verdict,
                    "detail": detail
                })

                progress_bar.progress((i + 1) / total)

            status_text.text("✅ Verification complete!")
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()

            real = sum(1 for r in results if r["verdict"] == "✅ REAL")
            mismatch = sum(1 for r in results if r["verdict"] == "⚠️ DETAILS MISMATCH")
            unverifiable = sum(1 for r in results if r["verdict"] == "⚠️ UNVERIFIABLE")
            hallucinated = sum(1 for r in results if r["verdict"] == "❌ HALLUCINATED")

            st.subheader("Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("✅ Real", real)
            col2.metric("⚠️ Details Mismatch", mismatch)
            col3.metric("⚠️ Unverifiable", unverifiable)
            col4.metric("❌ Hallucinated", hallucinated)

            st.subheader("Results")

            h1, h2, h3 = st.columns([3, 2, 5])
            h1.markdown("**Paper**")
            h2.markdown("**Verdict**")
            h3.markdown("**Detail**")
            st.markdown("---")

            for r in results:
                c1, c2, c3 = st.columns([3, 2, 5])
                c1.write(r["short_title"])
                c2.write(r["verdict"])
                c3.write(r["detail"])

                with st.expander("Full details"):
                    st.write(f"**Full title:** {r['title']}")
                    st.write(f"**Authors:** {r['authors']}")
                    st.write(f"**Year:** {r['year']}")
                    st.write(f"**DOI:** {r['doi'] if r['doi'] else 'Not provided'}")
                    # Google Scholar search link
                    gs_query = r['title'].replace(' ', '+')
                    gs_url = f"https://scholar.google.com/scholar?q={gs_query}"
                    st.markdown(f"[🔍 Search on Google Scholar]({gs_url})")

        else:
            st.warning("Please paste a bibliography first.")

# ─────────────────────────────────────────
# TAB 2 — CITATION FINDER
# ─────────────────────────────────────────
with tab2:
    st.title("🔍 Citation Finder")
    st.write("Search for real, verified academic papers. All filters are optional.")
    st.info("""
    **Note on DOI verification:**
    - Papers published after 2005 will generally have verified DOIs
    - Conference papers and arXiv preprints may not have DOIs even if real
    - Pre-2000 papers rarely have DOIs — this doesn't mean they're fake
    - Use the Google Scholar link in results to manually verify older papers
    """)

    query = st.text_input("Research question or topic (required)")

    st.subheader("Filters (all optional)")

    col1, col2 = st.columns(2)

    with col1:
        fields_of_study = st.multiselect(
            "Field of study",
            options=[
                "Business", "Management", "Psychology", "Economics",
                "Computer Science", "Medicine", "Biology", "Sociology",
                "Education", "Law", "Engineering", "Philosophy"
            ],
            placeholder="All fields"
        )
        author_name = st.text_input("Author name", placeholder="Leave blank for any author")

    with col2:
        year_range = st.slider("Year range", 1900, 2025, (2005, 2025))
        min_citations = st.slider("Minimum citation count", 0, 500, 0, step=10)

    with st.expander("⚙️ Advanced Settings — Adjust Scoring Weights"):
        st.write("Adjust how the combined score is calculated. Weights should add up to 100%.")

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            relevance_weight = st.slider("Relevance %", 0, 100, 50, step=5)
        with col_b:
            citation_weight = st.slider("Citation Count %", 0, 100, 30, step=5)
        with col_c:
            recency_weight = st.slider("Recency %", 0, 100, 20, step=5)

        total_weight = relevance_weight + citation_weight + recency_weight

        if total_weight != 100:
            st.warning(f"⚠️ Weights currently add up to {total_weight}%. Please adjust to total 100%.")
        else:
            st.success("✅ Weights add up to 100%")

    if st.button("Find Citations"):
        if not query:
            st.warning("Please enter a research question or topic.")
        elif total_weight != 100:
            st.warning("Please adjust scoring weights to total 100% before searching.")
        else:
            with st.spinner("Searching for papers..."):

                field_map = {
                    "Business": "business",
                    "Management": "management",
                    "Psychology": "psychology",
                    "Economics": "economics",
                    "Computer Science": "computer science",
                    "Medicine": "medicine",
                    "Biology": "biology",
                    "Sociology": "sociology",
                    "Education": "education",
                    "Law": "law",
                    "Engineering": "engineering",
                    "Philosophy": "philosophy"
                }

                params = {
                    "search": query,
                    "per_page": 20,
                    "mailto": "tarunsaiexperiment@gmail.com",
                }

                if fields_of_study:
                    field_filter = "|".join([field_map.get(f, f).lower() for f in fields_of_study])
                    params["filter"] = f"concepts.display_name.search:{field_filter}"

                response = requests.get("https://api.openalex.org/works", params=params)
                data = response.json()
                raw_papers = data.get("results", [])
                

            # ── Normalise OpenAlex format
            papers = []
            for p in raw_papers:
                doi_raw = p.get("doi", None)
                doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None

                authors = []
                for a in p.get("authorships", [])[:3]:
                    name = a.get("author", {}).get("display_name", "")
                    if name:
                        authors.append({"name": name})

                # Reassemble abstract from inverted index
                abstract = None
                inverted = p.get("abstract_inverted_index", None)
                if inverted:
                    try:
                        word_positions = []
                        for word, positions in inverted.items():
                            for pos in positions:
                                word_positions.append((pos, word))
                        word_positions.sort(key=lambda x: x[0])
                        abstract = " ".join([w for _, w in word_positions])
                    except Exception:
                        abstract = None

                papers.append({
                    "title": p.get("title", "No title"),
                    "authors": authors,
                    "year": p.get("publication_year", None),
                    "citationCount": p.get("cited_by_count", 0),
                    "abstract": abstract,
                    "externalIds": {"DOI": doi},
                    "fieldsOfStudy": [
                        c.get("display_name")
                        for c in p.get("concepts", [])[:3]
                    ]
                })

            # Apply filters
            filtered = []
            for p in papers:
                year = p.get("year") or 0
                citations = p.get("citationCount") or 0
                authors = p.get("authors", [])
                author_names_list = [a["name"].lower() for a in authors]

                if not (year_range[0] <= year <= year_range[1]):
                    continue
                if citations < min_citations:
                    continue
                if author_name:
                    if not any(author_name.lower() in a for a in author_names_list):
                        continue

                filtered.append(p)

            if not filtered:
                st.warning("No papers found matching your filters. Try relaxing them.")
            else:
                # Compute combined score
                citation_counts = [p.get("citationCount") or 0 for p in filtered]
                years = [p.get("year") or 1990 for p in filtered]

                max_citations = max(citation_counts) if max(citation_counts) > 0 else 1
                norm_citations = [c / max_citations * 100 for c in citation_counts]

                min_year, max_year = min(years), max(years)
                year_range_span = max_year - min_year if max_year != min_year else 1
                norm_recency = [(y - min_year) / year_range_span * 100 for y in years]

                total_papers = len(filtered)
                norm_relevance = [(total_papers - i) / total_papers * 100
                                  for i in range(total_papers)]

                combined_scores = [
                    (relevance_weight/100 * norm_relevance[i]) +
                    (citation_weight/100 * norm_citations[i]) +
                    (recency_weight/100 * norm_recency[i])
                    for i in range(total_papers)
                ]

                for i, p in enumerate(filtered):
                    p["combined_score"] = round(combined_scores[i], 1)

                filtered.sort(key=lambda x: x["combined_score"], reverse=True)

                # Verify DOIs
                st.subheader(f"Found {len(filtered)} papers — verifying DOIs...")
                progress = st.progress(0)
                status = st.empty()

                for i, p in enumerate(filtered):
                    doi = p.get("externalIds", {}).get("DOI", None)
                    title_short = (p.get("title") or "")[:40]
                    status.text(f"Verifying {i+1} of {len(filtered)}: {title_short}")

                    if doi:
                        cr = requests.get(f"https://api.crossref.org/works/{doi}")
                        time.sleep(0.2)
                        p["doi"] = doi
                        p["doi_status"] = "✅ Verified" if cr.status_code == 200 else "❌ Not verified"
                    else:
                        p["doi"] = None
                        p["doi_status"] = "⚠️ No DOI"

                    progress.progress((i + 1) / len(filtered))

                status.text("✅ Done!")
                time.sleep(1)
                status.empty()
                progress.empty()

                # Display results
                st.subheader("Results — ranked by combined score")

                h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1])
                h1.markdown("**Title**")
                h2.markdown("**Year**")
                h3.markdown("**Citations**")
                h4.markdown("**DOI**")
                h5.markdown("**Score**")
                st.markdown("---")

                for p in filtered:
                    title = p.get("title", "No title")
                    short_title = title[:45] + "..." if len(title) > 45 else title
                    year = p.get("year", "?")
                    citations = p.get("citationCount", 0)
                    authors = p.get("authors", [])
                    author_display = ", ".join([a["name"] for a in authors[:2]])
                    abstract = p.get("abstract", "No abstract available")
                    score = p.get("combined_score", 0)

                    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                    c1.write(short_title)
                    c2.write(year)
                    c3.write(citations)
                    c4.write(p["doi_status"])
                    c5.write(f"{score}")

                    with st.expander("Full details"):
                        st.write(f"**Full title:** {title}")
                        st.write(f"**Authors:** {author_display}")
                        st.write(f"**Year:** {year}")
                        st.write(f"**Citations:** {citations}")
                        st.write(f"**DOI:** {p['doi'] if p['doi'] else 'Not available'}")
                        st.write(f"**DOI Status:** {p['doi_status']}")
                        st.write(f"**Combined Score:** {score}/100")
                        if abstract and len(abstract) > 300:
                            st.write(f"**Abstract:** {abstract[:300]}...")
                        else:
                            st.write(f"**Abstract:** {abstract}")