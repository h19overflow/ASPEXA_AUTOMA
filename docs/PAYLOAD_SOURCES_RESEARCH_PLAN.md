# Payload Sources Research Plan: Finding Proven Jailbreaks & Arabic Prompts

## Executive Summary

**Goal**: Find publicly available, proven adversarial prompts with documented POCs before implementing vector database infrastructure.

**Priority**:
1. ✅ **Proven English jailbreaks** with POCs (GPT-4, Claude, Gemini, Llama)
2. ✅ **Arabic dialect prompts** (MSA, Egyptian, Gulf, Levantine)
3. ✅ **Multilingual attacks** (code-switching, translation exploits)

**Why This First**: Don't build a library with no books. Need to validate:
- Do public datasets exist with quality examples?
- Are there enough POCs to make retrieval-based generation valuable?
- What's the quality gap between English vs Arabic prompts?

---

## Research Track 1: Proven English Jailbreaks with POCs

### Primary Sources to Search

#### 1. **Academic Papers with Datasets**

**Search Strategy**:
```
Google Scholar queries:
- "jailbreak prompts dataset" + "github" after:2024
- "adversarial prompts" + "LLM" + "evaluation benchmark" after:2024
- "red teaming language models" + "public dataset" after:2024
- "prompt injection attacks" + "proof of concept" after:2024

Focus on papers from 2024-2025 (GPT-4o, Claude 3.5, Gemini 2.0)
```

**Known Starting Points** (2024-2025):
- **Anthropic Red Team Dataset**: Search for "Anthropic Claude 3.5 red team prompts"
- **OpenAI Moderation Research**: "OpenAI GPT-4o jailbreak evaluation"
- **Google DeepMind Safety**: "Gemini 2.0 safety benchmarks"
- **HarmBench**: "HarmBench 2024 adversarial prompts"
- **WildJailbreak**: "WildJailbreak dataset 2024" (recent large-scale study)
- **JailbreakBench**: "JailbreakBench leaderboard 2024"

**What to Extract**:
- [ ] GitHub repo links
- [ ] Number of prompts (need >100 for useful library)
- [ ] Attack categories (jailbreak, injection, data leak, etc.)
- [ ] Target models (GPT-4, Claude, Gemini, etc.)
- [ ] Success rates documented?
- [ ] License (MIT, Apache, CC-BY?)

#### 2. **GitHub Repositories**

**Search Queries**:
```
GitHub search:
- "jailbreak prompts" language:Python stars:>100
- "adversarial prompts LLM" language:Python
- "prompt injection dataset"
- "AI red team" "prompts"
- "ChatGPT jailbreak collection"

Filter by:
- Recently updated (2025)
- Has actual prompt files (.txt, .json, .csv)
- Has README with methodology
```

**Known Repos to Check** (Active in 2024-2025):
- [ ] **awesome-chatgpt-prompts**: Check for adversarial section
- [ ] **LLM-Attacks**: (Zou et al. 2023) - Adversarial suffix generation
- [ ] **garak**: Check their probe library (you already use this!)
- [ ] **JailbreakBench**: Latest benchmark with GPT-4o/Claude 3.5 attacks
- [ ] **prompt-injection-defenses**: Usually includes attack examples
- [ ] **PAIR** (Prompt Automatic Iterative Refinement): 2024 jailbreak method
- [ ] **Crescendo Multi-Turn**: 2024 multi-turn jailbreak dataset

**Validation Criteria**:
For each repo, check:
- [ ] Has POC examples (not just descriptions)
- [ ] Includes target model + version (GPT-4o, Claude 3.5, Gemini 2.0+)
- [ ] Shows actual attack/response pairs
- [ ] Maintained (commits in last 6 months - since June 2024)
- [ ] License allows commercial use (MIT, Apache 2.0, CC-BY)

#### 3. **HuggingFace Datasets**

**Search Strategy**:
```
HuggingFace search:
- "jailbreak" (datasets section)
- "adversarial prompts"
- "red team"
- "harmful prompts"
- "safety evaluation"

Sort by: Downloads (popular = validated)
```

**Known Datasets to Check** (2024-2025):
- [ ] **WildJailbreak**: 262K+ vanilla jailbreak prompts (2024)
- [ ] **JailbreakBench**: Curated benchmark for GPT-4o/Claude 3.5
- [ ] **anthropic-hh-rlhf**: Has harmful/harmless pairs (updated 2024)
- [ ] **PKU-SafeRLHF-30K**: Safety-focused dataset (2024 update)
- [ ] **lmsys-chat-1m**: Real conversations (may contain jailbreaks)
- [ ] **HarmfulQA**: Recent adversarial QA dataset
- [ ] **ToxicChat**: 10K+ toxic prompts with annotations

**What to Extract**:
- [ ] Download size (estimate # of prompts)
- [ ] Format (JSON, JSONL, Parquet)
- [ ] Fields available (prompt, response, model, success_flag)
- [ ] Quality assessment in README

#### 4. **Security Conferences & CTF Writeups**

**Search Strategy**:
```
Google queries:
- "DEF CON" + "LLM jailbreak" + "writeup"
- "Black Hat" + "prompt injection" + "POC"
- "AI Village CTF" + "prompts"
- "MLSecOps" + "adversarial examples"

Sites to check:
- defcon.org/html/links/dc-archives.html
- github.com/AI-Village
- ctftime.org (search "AI" or "LLM")
```

**What to Extract**:
- [ ] Winning CTF prompts (highly creative)
- [ ] Novel attack vectors (not in papers)
- [ ] Target-specific exploits (GPT-4 vs Claude differences)

#### 5. **Twitter/X & Discord Communities**

**Why**: Researchers often share new jailbreaks before publication

**Search Strategy**:
```
Twitter/X (2024-2025):
- Follow @alexalbert__, @goodside, @simonw, @repligate (LLM researchers)
- Search: "jailbreak GPT-4o" filter:media after:2024-06-01
- Search: "Claude 3.5 Sonnet prompt injection" after:2024-06-01
- Search: "Gemini 2.0 jailbreak" filter:media after:2024-12-01

Discord (Active Communities):
- EleutherAI server (#safety channel)
- HuggingFace server (#ethics-and-society)
- LangChain server (#security)
- Anthropic server (if accessible)
```

**What to Collect**:
- [ ] Screenshot prompts (OCR if needed)
- [ ] Novel techniques (before papers)
- [ ] Real-world exploits (not academic)

---

## Research Track 2: Arabic Dialect Prompts

### Challenge: Arabic AI Safety Research is Nascent

**Reality Check**:
- Most LLM safety research is English-focused
- Arabic jailbreaks are under-documented
- Need to find: academic research, native speaker communities, translation datasets

### Primary Sources to Search

#### 1. **Arabic NLP Research**

**Search Strategy**:
```
Google Scholar (Arabic + English) - 2024-2025:
- "Arabic language models" + "safety" after:2024
- "نماذج اللغة العربية" + "اختبار الأمان" after:2024
- "Arabic prompt engineering" after:2024
- "multilingual adversarial attacks" + "Arabic" after:2024
- "code-switching attacks" + "Arabic" after:2024

Focus: EMNLP 2024, ACL 2024, NAACL 2025, EACL 2024
```

**Known Research Groups**:
- [ ] **QCRI (Qatar Computing Research Institute)**: Arabic NLP leaders
- [ ] **NYU Abu Dhabi**: Arabic AI research
- [ ] **KAUST (Saudi Arabia)**: Arabic language models
- [ ] **Cairo University**: Arabic computational linguistics

**What to Find**:
- [ ] Arabic-specific jailbreak patterns
- [ ] Cultural context exploits (different than English)
- [ ] Dialectal variation research (MSA vs Egyptian vs Gulf)

#### 2. **Arabic AI Model Providers**

**Strategy**: Check safety docs from Arabic-supporting models

**Models to Research** (2024-2025 Latest Versions):
```
Search for safety/red-teaming docs:
- OpenAI GPT-4o & o1 (enhanced Arabic support)
- Anthropic Claude 3.5 Sonnet & Opus (multilingual)
- Google Gemini 2.0 Flash & Pro (128+ languages)
- Cohere Command R+ (multilingual)
- Jais 30B & 13B (Arabic-specific LLM from G42 - 2024 update)
- AceGPT v2 (Arabic LLM from MBZUAI - 2024)
- ALLaM (IBM Arabic LLM - 2024)
- Meta Llama 3.3 (improved Arabic)
```

**What to Extract**:
- [ ] Do they publish Arabic safety benchmarks?
- [ ] Example prompts used for testing
- [ ] Known vulnerabilities in Arabic
- [ ] Refusal patterns in Arabic

#### 3. **Arabic Developer Communities**

**Platforms to Search**:
```
GitHub:
- Search: "Arabic" + "chatbot" + "prompts"
- Search: "العربية" + "GPT"
- Check repos from Saudi/UAE/Egypt developers

Reddit:
- r/arabs (tech discussions)
- r/LanguageTechnology (Arabic flair)

Arabic Forums:
- hsoub.com (Arabic dev community)
- stackoverflow.com/questions/tagged/arabic
```

**What to Find**:
- [ ] Community-generated prompt collections
- [ ] Translation of English jailbreaks
- [ ] Native Arabic adversarial prompts
- [ ] Dialect-specific examples

#### 4. **Multilingual Jailbreak Research**

**Search Strategy**:
```
Papers on cross-lingual attacks:
- "multilingual jailbreak"
- "translation-based adversarial attacks"
- "code-switching prompt injection"
- "low-resource language attacks"

GitHub:
- "multilingual prompts"
- "translation attack"
```

**Techniques to Find**:
- [ ] English jailbreak → Arabic translation → attack
- [ ] Code-switching exploits (mix English + Arabic)
- [ ] Script-based attacks (Arabic script lookalikes)

#### 5. **Arabic Social Engineering Datasets**

**Search Strategy**:
```
Look for:
- Arabic phishing email datasets
- Arabic social engineering examples
- Arabic persuasion techniques research
- Cultural context for manipulation

Sites:
- HuggingFace: "Arabic" + "phishing"
- Kaggle: "Arabic text classification"
- Academic datasets: "Arabic sentiment" (can adapt for adversarial)
```

**Why Useful**:
- Phishing = social engineering = similar to jailbreaks
- Shows culturally-aware persuasion patterns
- Can adapt for AI jailbreaking context

---

## Research Track 3: Garak Probe Analysis (You Already Have This!)

### Existing Asset: Garak Framework

**You're already using Garak** - let's mine it for proven prompts!

**Research Tasks**:

#### 1. **Audit Your Garak Scan Results**

**Location**: `S3: scans/{campaign_id}/garak_results.json`

**Analysis Script** (pseudocode):
```python
# Collect all successful Garak probes from past campaigns
import json
from collections import Counter

successful_probes = []
for campaign in load_all_campaigns():
    results = load_garak_results(campaign.id)

    for probe in results["probes"]:
        if probe["score"] > 0.5:  # Successful
            successful_probes.append({
                "probe_name": probe["name"],
                "payload": probe["prompt"],
                "score": probe["score"],
                "target_model": campaign.target_model,
                "defense_bypassed": probe["detector_triggered"]
            })

# Find most successful probe types
probe_types = Counter([p["probe_name"] for p in successful_probes])
print(f"Top successful probes: {probe_types.most_common(10)}")

# Export to JSON for library seeding
save_to_library(successful_probes, "garak_proven_payloads.json")
```

**What You'll Get**:
- [ ] Real POCs from YOUR campaigns
- [ ] Already validated against your targets
- [ ] Metadata: detector scores, defense signals
- [ ] Immediate dataset (no external research needed)

#### 2. **Analyze Garak Source Code**

**Location**: Garak GitHub repo (you're using it)

**Files to Extract Prompts From**:
```
garak/probes/
├── dan.py              # DAN (Do Anything Now) jailbreaks
├── encoding.py         # Base64, hex encoding attacks
├── gcg.py              # Greedy Coordinate Gradient attacks
├── malwaregen.py       # Malware generation prompts
├── packagehallucination.py  # Code injection
└── ... (50+ probe files)
```

**Extraction Script**:
```python
# Parse Garak source for prompt templates
import ast
import os

def extract_garak_prompts(garak_source_dir):
    prompts = []

    for probe_file in os.listdir(f"{garak_source_dir}/garak/probes/"):
        with open(probe_file) as f:
            tree = ast.parse(f.read())

        # Find prompt strings in class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.Str):
                if len(node.s) > 50:  # Likely a prompt
                    prompts.append({
                        "source": probe_file,
                        "text": node.s,
                        "probe_type": extract_probe_type(probe_file)
                    })

    return prompts
```

**Expected Yield**: 200-500 proven prompts with metadata

---

## Research Track 4: Competition & CTF Platforms

### AI Red Teaming Competitions

**Platforms to Check**:

#### 1. **AI Village (DEF CON)**
```
URLs to search:
- aivillage.org
- github.com/AI-Village/CTF-Challenges

What to find:
- Past CTF challenges (2022, 2023, 2024)
- Winning submissions
- Prompt datasets used for challenges
```

#### 2. **Kaggle Competitions**
```
Search:
- "LLM safety"
- "adversarial prompts"
- "jailbreak detection"

Check:
- Competition datasets (public after competition ends)
- Winner solutions (often shared on GitHub)
- Discussion forums (participants share techniques)
```

#### 3. **HackerOne Bug Bounties**
```
Search:
- "AI" or "LLM" in HackerOne disclosed reports
- OpenAI bug bounty disclosures
- Anthropic security reports

What to extract:
- Disclosed prompt injection vulnerabilities
- POC examples (if public)
- Remediation strategies (shows what works)
```

---

---

## Phased Search Execution Plan

### Phase 1: Foundation (Week 1) - Internal Assets + Quick Wins

**Goal**: Extract 250-700 proven prompts from existing resources with zero external dependencies.

#### Day 1-2: Internal Assets Extraction
- [ ] **Day 1 Morning**: Extract successful probes from your Garak S3 results
  - Run analysis script on past campaigns (2024-2025 only)
  - Filter: score > 0.5, has response, date >= 2024-01-01
  - Export to `garak_proven_payloads.json`
  - Estimate: 50-200 proven prompts

- [ ] **Day 1 Afternoon**: Clone Garak source, extract prompt templates
  - Clone latest Garak repo (2024-2025 commits)
  - Parse all `garak/probes/*.py` files
  - Extract prompt strings + metadata
  - Categorize by attack type (jailbreak, injection, leak)
  - Estimate: 200-500 templates

- [ ] **Day 2**: Consolidate & validate internal dataset
  - Merge S3 results + Garak templates
  - Deduplicate using fuzzy matching
  - Tag with metadata: source, type, target_model
  - Quality check: remove outdated/broken prompts
  - Export: `phase1_internal_prompts.json`

**Phase 1 Deliverable**: 250-700 prompts with POCs (validated, recent, proven)

---

### Phase 2: Public Datasets (Week 2) - Academic & Community Sources

**Goal**: Collect 500-2000 additional prompts from public research and verified repositories.

#### Day 3-4: Academic Papers & Benchmarks
- [ ] **Day 3 Morning**: Google Scholar search (2024-2025 papers)
  - Search: "jailbreak dataset" after:2024
  - Target: WildJailbreak, JailbreakBench, HarmBench updates
  - Download papers + supplementary materials
  - Extract dataset links (HuggingFace, GitHub, Zenodo)

- [ ] **Day 3 Afternoon**: Process academic datasets
  - Download top 5 datasets (prioritize 2024-2025)
  - Convert to standardized format
  - Extract metadata: model, attack type, success rate
  - Quality filter: only prompts with POC responses

- [ ] **Day 4 Morning**: GitHub repository mining (2024-2025 repos)
  - Search: Updated since June 2024
  - Clone: JailbreakBench, PAIR, Crescendo, latest LLM-Attacks
  - Validate licensing (MIT, Apache, CC-BY only)
  - Extract prompt files (.json, .txt, .csv)

- [ ] **Day 4 Afternoon**: Repository consolidation
  - Standardize format across all repos
  - Deduplicate against Phase 1 dataset
  - Tag with source, license, recency
  - Export: `phase2_academic_prompts.json`

**Phase 2 Deliverable**: 500-2000 additional prompts from verified public sources (2024-2025 only)

---

### Phase 3: Community & Cutting-Edge (Week 3) - Fresh Discoveries

**Goal**: Collect 200-500 recent prompts from active communities and identify emerging techniques.

#### Day 5-6: HuggingFace & Community Platforms
- [ ] **Day 5 Morning**: HuggingFace datasets (2024-2025 uploads)
  - Search: "jailbreak", "adversarial", "red team" (uploaded after 2024-01-01)
  - Download: WildJailbreak, ToxicChat, HarmfulQA, latest updates
  - Filter: datasets with >1K downloads (quality indicator)
  - Convert to standardized format

- [ ] **Day 5 Afternoon**: Community mining (Twitter/X, Reddit)
  - Twitter: Search "jailbreak GPT-4o" after:2024-06-01
  - Twitter: Search "Claude 3.5 Sonnet bypass" after:2024-06-01
  - Reddit: r/ChatGPT, r/LocalLLaMA, r/ArtificialIntelligence (2024 posts)
  - Extract novel techniques not in papers
  - Screenshot + OCR if needed

- [ ] **Day 6 Morning**: Discord & specialized communities
  - EleutherAI #safety (last 6 months)
  - HuggingFace #ethics-and-society (last 6 months)
  - LangChain #security (recent discussions)
  - Collect novel prompts, tag as "community_2024"

- [ ] **Day 6 Afternoon**: CTF & Bug Bounty disclosures
  - AI Village DEF CON 2024 challenges
  - HackerOne disclosed LLM vulnerabilities (2024)
  - Kaggle LLM safety competitions (2024)
  - Extract POCs from writeups

**Phase 3 Deliverable**: 200-500 cutting-edge prompts (last 12 months, bleeding-edge techniques)

---

### Phase 4: Arabic & Multilingual (Week 4) - Targeted Language Research

**Goal**: Collect 20-100 Arabic prompts and assess quality vs English. Determine translation vs native approach.

#### Day 7-8: Arabic Academic & Model Research
- [ ] **Day 7 Morning**: Arabic academic papers (2024-2025)
  - Google Scholar: "Arabic LLM safety" after:2024
  - Target conferences: EMNLP 2024, ACL 2024, ArabicNLP 2024
  - Check QCRI, KAUST, NYU Abu Dhabi, MBZUAI publications
  - Extract any Arabic adversarial prompt examples

- [ ] **Day 7 Afternoon**: Arabic model documentation
  - Jais 30B safety documentation (G42 - 2024 update)
  - AceGPT v2 evaluation reports (MBZUAI - 2024)
  - ALLaM safety benchmarks (IBM - 2024)
  - Meta Llama 3.3 Arabic safety tests
  - Extract test prompts from reports

- [ ] **Day 8 Morning**: Arabic developer communities
  - GitHub: "Arabic" + "chatbot" (updated 2024-2025)
  - GitHub: "العربية" + "نموذج لغوي" (updated 2024-2025)
  - hsoub.com: Search "GPT" + "اختبار" (testing discussions)
  - Stack Overflow Arabic tags (2024 questions)

- [ ] **Day 8 Afternoon**: Multilingual datasets mining
  - HuggingFace: "multilingual" + "adversarial" (with Arabic)
  - Search: Code-switching attack papers (English-Arabic mix)
  - Translation attack datasets
  - Export: `phase4_arabic_prompts.json`

**Phase 4 Deliverable**: 20-100 Arabic prompts + quality assessment report

---

### Phase 5: Consolidation & Analysis (Week 5) - Final Dataset Creation

**Goal**: Merge all phases, deduplicate, validate, and create production-ready dataset.

#### Day 9-10: Final Consolidation
- [ ] **Day 9 Morning**: Merge all phase datasets
  - Combine Phase 1-4 outputs
  - Total expected: 1000-3000 English + 20-100 Arabic
  - Standardize schema across all sources
  - Validate: all fields present, correct types

- [ ] **Day 9 Afternoon**: Advanced deduplication
  - Exact match removal (same text)
  - Fuzzy matching (90%+ similarity)
  - Semantic deduplication (use sentence-transformers)
  - Keep highest quality version when duplicates found

- [ ] **Day 10 Morning**: Quality scoring & filtering
  - Assign quality score (1-5) to each prompt:
    - 5: Has POC, response, score, recent (2024-2025)
    - 4: Has POC, response, no score
    - 3: Has POC, no response
    - 2: No POC, but from trusted source
    - 1: Incomplete/unverified
  - Filter: Keep score >= 3 for library
  - Export low-quality separately for future research

- [ ] **Day 10 Afternoon**: Final dataset export & documentation
  - Export: `proven_prompts_library_v1.json`
  - Create metadata summary:
    - Total count by language
    - Count by attack type
    - Count by target model
    - Recency distribution (2024 vs 2025)
    - Source breakdown
  - Generate quality report
  - Create research findings document

**Phase 5 Deliverable**: Production-ready dataset + comprehensive research report

---

## Phase-by-Phase Summary

| Phase | Duration | Focus | Expected Output | Key Milestone |
|-------|----------|-------|-----------------|---------------|
| **Phase 1** | Week 1 (2 days) | Internal assets (S3 + Garak) | 250-700 prompts | ✅ Proven baseline established |
| **Phase 2** | Week 2 (2 days) | Academic papers + GitHub (2024-2025) | 500-2000 prompts | ✅ Public research integrated |
| **Phase 3** | Week 3 (2 days) | Community + cutting-edge (last 12 months) | 200-500 prompts | ✅ Latest techniques captured |
| **Phase 4** | Week 4 (2 days) | Arabic + multilingual (2024-2025) | 20-100 Arabic prompts | ✅ Language gap assessed |
| **Phase 5** | Week 5 (2 days) | Consolidation + quality control | Final dataset (1000-3000 total) | ✅ Production-ready library |

**Total Timeline**: 5 weeks (10 working days)
**Expected Final Count**: 1000-3000 English prompts + 20-100 Arabic prompts
**Quality Target**: >80% with POCs, >60% from 2024-2025 sources

---

## Expected Outcomes

### Success Criteria (Minimum Viable)

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| **Total English prompts** | 1000+ | 3000+ |
| **Prompts with POCs** | 500+ | 1500+ |
| **Target models covered** | GPT-4o, Claude 3.5, Gemini 2.0 | +Llama 3.3, Mistral, Qwen |
| **Attack categories** | 5+ (jailbreak, injection, leak, bypass, multi-turn) | 10+ |
| **Arabic prompts** | 20+ | 100+ |
| **Recent prompts** (2024-2025) | 600+ (>60%) | 2000+ (>80%) |
| **Quality score ≥3** | 700+ (>70%) | 2500+ (>85%) |

### Data Schema (Standardized Format)

```json
{
  "payload_id": "uuid",
  "source": "garak|github|paper|community",
  "source_url": "https://...",
  "prompt_text": "Ignore previous instructions...",
  "attack_type": "jailbreak|injection|leak|bypass",
  "target_model": "gpt-4-turbo|claude-3-opus|gemini-pro",
  "target_defense": "keyword_filter|content_filter|rate_limit",
  "has_poc": true,
  "success_response": "Sure, I can help with that...",
  "success_score": 0.85,
  "converters_used": ["base64", "homoglyph"],
  "framing_type": "debugging|compliance|research",
  "language": "en|ar|es",
  "dialect": "msa|egyptian|gulf" (if Arabic),
  "date_discovered": "2024-01-15",
  "license": "mit|apache|cc-by",
  "metadata": {
    "author": "researcher_name",
    "paper_title": "...",
    "github_stars": 1234
  }
}
```

### Deliverable: Research Report

**File**: `docs/PAYLOAD_RESEARCH_FINDINGS.md`

**Sections**:
1. **Executive Summary**
   - Total prompts found
   - Quality assessment
   - Recommendation: Proceed with library or not?

2. **Source Breakdown**
   - Prompts per source
   - Quality ratings
   - License summary

3. **Coverage Analysis**
   - Models covered
   - Attack types represented
   - Temporal distribution (how recent?)

4. **Arabic Findings**
   - Number of Arabic prompts found
   - Quality vs English
   - Recommendation: Translation vs native generation

5. **Gap Analysis**
   - What's missing?
   - What attack types underrepresented?
   - Should we generate synthetic prompts to fill gaps?

6. **Next Steps**
   - If >500 quality prompts: Proceed with ChromaDB library
   - If <500: Re-evaluate retrieval approach
   - If Arabic <50: Focus on translation + English library

---

## Web Search Queries (Copy-Paste Ready)

### English Prompts

#### GitHub
```
"jailbreak prompts" language:Python stars:>50
"adversarial LLM prompts" language:Python
"prompt injection dataset" language:Python
garak probes extension:py
"chatgpt jailbreak" "proof of concept"
"claude jailbreak" language:Python
```

#### Google Scholar
```
"jailbreak prompts" "language models" dataset
"adversarial prompts" "GPT-4" evaluation
"red teaming" "large language models" benchmark
"prompt injection attacks" "proof of concept"
HarmBench adversarial prompts
```

#### HuggingFace
```
jailbreak
adversarial prompts
red team evaluation
safety benchmark
harmful prompts
```

#### Google (General)
```
"jailbreak prompts collection" github
"adversarial LLM prompts" dataset download
"AI red team" "public dataset"
"prompt injection examples" site:github.com
DEF CON "AI Village" CTF prompts
```

### Arabic Prompts

#### Google Scholar (Arabic + English)
```
"Arabic language models" safety evaluation
نماذج اللغة العربية اختبار الأمان
"multilingual adversarial attacks" Arabic
"code-switching" "prompt injection" Arabic
Jais LLM safety benchmark
```

#### GitHub (Arabic)
```
العربية chatbot prompts
Arabic "jailbreak" language:Python
"Arabic prompts" "GPT-4"
Jais safety evaluation
AceGPT testing
```

#### Google (Arabic Communities)
```
site:hsoub.com "GPT" "اختراق"
"Arabic AI prompts" community
"Arabic chatbot" "adversarial"
"نماذج اللغة" "اختبار الأمان"
```

---

## Risk Assessment

### Potential Blockers

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Few public Arabic prompts** | High | High | Focus on translation + native generation |
| **No POCs in datasets** | Medium | High | Extract from Garak results instead |
| **Licensing issues** | Low | Medium | Filter to MIT/Apache/CC-BY only |
| **Outdated prompts** (pre-2023) | Medium | Medium | Prioritize 2024 sources |
| **Poor quality (no responses)** | Medium | Low | Validate with test runs before storing |

---

## Success Metrics (Post-Research)

### Decision Framework (Updated for 2024-2025 Quality Standards)

**IF** we find (after Phase 5 consolidation):

#### English Prompts Decision Tree
- ✅ **>1000 prompts (score ≥3, >60% from 2024-2025)** → **Proceed with ChromaDB vector library**
  - High confidence: Retrieval-based generation will outperform pure LLM
  - Action: Implement ChromaDB + embedding search

- ⚠️ **500-1000 prompts (mixed quality/recency)** → **Hybrid: SQLite cache + selective retrieval**
  - Medium confidence: Useful for proven attacks, LLM for novel
  - Action: Build simpler SQLite exact-match cache first

- ❌ **<500 prompts OR <40% from 2024-2025** → **Abandon retrieval, improve LLM prompts**
  - Low confidence: Dataset too small/outdated to justify infrastructure
  - Action: Focus on better prompt engineering for LLM generation

#### Arabic Prompts Decision Tree
- ✅ **>100 Arabic prompts (score ≥3)** → **Build bilingual library now**
  - Action: Multilingual embeddings (paraphrase-multilingual-MiniLM)

- ⚠️ **50-100 Arabic prompts** → **Translation-first + seed library in parallel**
  - Action: English→Arabic translation, store successful translations

- ⚠️ **20-50 Arabic prompts** → **Translation-only approach**
  - Action: Translate English prompts dynamically, evaluate quality

- ❌ **<20 Arabic prompts** → **Pure LLM generation in Arabic (no retrieval)**
  - Action: Gemini 2.0 native Arabic generation, no library needed

#### Recency Quality Gate
- **If >80% prompts from 2024-2025**: ✅ High quality, proceed confidently
- **If 60-80% from 2024-2025**: ⚠️ Good quality, proceed with caution
- **If 40-60% from 2024-2025**: ⚠️ Mixed quality, filter to recent only
- **If <40% from 2024-2025**: ❌ Too outdated, restart with stricter filters

---

## Next Actions (After This Research)

### If Research is Successful (>500 prompts):
1. Implement ChromaDB (1 day)
2. Seed library with prompts (1 day)
3. Implement retrieval in `payload_generator.py` (1 day)
4. A/B test: retrieval vs pure generation (1 week)

### If Research is Partial (200-500 prompts):
1. Build simple SQLite cache (no embeddings) (1 day)
2. Store top 200 proven prompts (1 day)
3. Exact match retrieval (faster than vector search) (1 day)
4. Evaluate before investing in ChromaDB

### If Arabic Research Fails (<50 prompts):
1. Focus on translation approach (2 days)
2. Build English library only (3 days)
3. Revisit Arabic native generation in 6 months

---

## Tools & Scripts Needed

### 1. Garak Results Parser
```python
# scripts/parse_garak_results.py
# Extracts successful probes from S3
# Outputs: garak_proven_payloads.json
```

### 2. GitHub Repo Scraper
```python
# scripts/scrape_github_prompts.py
# Clones repos, extracts prompts from .txt/.json files
# Outputs: github_prompts.json
```

### 3. HuggingFace Dataset Loader
```python
# scripts/load_hf_datasets.py
# Downloads + converts HF datasets
# Outputs: hf_prompts.json
```

### 4. Deduplication Script
```python
# scripts/deduplicate_prompts.py
# Uses fuzzy matching or embeddings
# Removes near-duplicates
```

### 5. Quality Validator
```python
# scripts/validate_quality.py
# Checks: has_poc, has_response, is_recent
# Tags quality score (1-5)
```

---

**Start with Day 1 (Garak extraction) - you already have the data! Then expand outward based on what you find.**

Want me to implement any of these scripts to help with the research?
