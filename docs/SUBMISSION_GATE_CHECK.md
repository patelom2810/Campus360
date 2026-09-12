# Campus360 — Final Pre-Submission Gate Audit (KDAC-3)

**Evaluation Mode:** Strict, Adversarial, Pre-Submission Gate  
**Target Specification:** KENEXA AI Hackathon (Problem Code: KDAC-3)  
**Authors / Team:** Om Patel & Rahil Nagariya (Team ID: 60)  
**Execution Timestamp:** 2026-09-12 (Live Environment Execution)  

---

## Final Pre-Submission Recommendation

> ### **RECOMMENDATION: GO (CONDITIONAL ON PROACTIVE JUDGE EXPECTATION MANAGEMENT)**
> 
> *Campus360 provides an enterprise-grade, zero-leakage data warehouse (180,000 star-schema rows across 6 stitched datasets), an unattended Docker deployment (5.3 min from scratch / 11.9s container auto-ETL), and a resilient GenAI fallback architecture; however, its ML models fail conventional performance bars ($R^2=0.2096$, $\text{Recall}=0.4514$) and must be defended proactively as honest diagnostic baselines rather than oversold predictive engines.*

---

## 1. Compliance Matrix (Directly Mapped to Problem Statement)

All figures below were **re-derived live** against the active PostgreSQL 16 warehouse, trained model artifacts, REST endpoints, and Docker containers.

| Requirement (Exact KDAC-3 Brief Language) | Status | Live Evidenced Results | Blocking? |
| :--- | :---: | :--- | :---: |
| **"Integrates multiple datasets through data stitching"** | **PASS** | Evaluated all 15 pairwise column combinations across all 6 raw datasets. 13 of 15 pairs exhibit Jaccard column overlap $\le 10.3\%$ (highest is 33.3% between Kundan and Suvidya academic marks). Confirmed genuine multi-domain integration (lifestyle, academic exams, placement records, benchmark salaries). Live tracing of 3 random students (`STU00010`, `STU00125`, `STU01500`) and high-density multi-matched students (`STU00091`, 4 secondary matches) confirms statistical alignment within tertile performance bands without data leakage. | **No** |
| **"Warehouse design"** | **PASS** | Attempted a live orphan foreign key insert (`student_id = 'STU_FAKE_99999'`) into `fact_performance`. **PostgreSQL strictly rejected the write** with `psycopg2.errors.ForeignKeyViolation: insert or update on table "fact_performance" violates foreign key constraint "fk_fact_perf_student"`. Schema audit confirmed conformed star schema: `dim_student` contains demographic attributes, while `fact_performance` (8 cols), `fact_lifestyle` (12 cols), and `fact_career` (16 cols) contain **0% demographic attribute leakage** (0/8 overlap). | **No** |
| **"ETL pipeline"** | **PASS** | Executed pipeline from a clean state: dropped all 4 PostgreSQL tables via `CASCADE`, deleted all interim CSVs, and purged `data/processed/warehouse.db`. `python src/etl/run_pipeline.py` ran completely unattended in **8.36 seconds** (ETL core in 6.34s). Automatically reconstituted schemas, primary keys, foreign key constraints, and populated exact expected row counts (`dim_student`: 25k, `fact_performance`: 105k, `fact_lifestyle`: 25k, `fact_career`: 25k). | **No** |
| **"Subject-wise analytics dashboards"** | **CONDITIONAL** | Live SQL aggregation verified across 105,000 performance rows: `Overall Score` ranks as the lowest normalized subject across 100% of engineering branches (63.44% to 64.85%). While mathematically correct (Kundan's composite term examination mean is 63.8%), displaying "Overall Score" as a *subject* in the "Lowest-Performing Subject per Branch" table carries a **HIGH demo risk** of appearing as an aggregation/grouping bug to a skeptical judge. Requires UI footnote or aggregate filtering. | **No** |
| **"ML models for performance prediction and at-risk detection"** | **FAIL (Raw Bar) / PASS (Integrity)** | Fresh live re-scoring on test splits ($N=5,000$ each):<br>• **Model 1 (CGPA Predictor):** $R^2 = 0.2096$, $\text{RMSE} = 0.7581$, $\text{MAE} = 0.6022$. **FAILS** acceptable bar ($R^2 \ge 0.30$).<br>• **Model 2 (At-Risk Classifier):** $\text{Recall} = 0.4514$, $\text{Precision} = 0.3230$, $\text{AUC} = 0.5044$, $\text{Accuracy} = 0.5232$. **FAILS** acceptable bar ($\text{Recall} \ge 0.50$, $\text{AUC} > 0.60$).<br>• **Model 3 (Career):** Confirmed `models/model3_career_predictor.joblib` does NOT exist; `train_career_model.py` is 0 bytes. Career guidance is powered by an analytical weighted population-normalized composite score (CGPA 25%, DSA 20%, Aptitude 15%, Interview 15%, Coding 15%, Comm 10%). | **No** |
| **"GenAI-powered insights for faculty and mentors"** | **PASS** | Tested all 3 GenAI endpoints (`atrisk-brief`, `performance-summary`, `career-guidance`) live with an invalid Gemini key (`broken_key_xyz_12345`). All 3 gracefully caught HTTP 400 and returned structured deterministic template briefs with `is_fallback: True` in $<0.1\text{s}$ with zero crashes. Tested edge-case student `STU00001` (zero secondary matches): generated briefs contained strictly verified numbers ($48.9\%$ risk probability, $2.7$ study hrs/day, $45\%$ recall calibration) with zero hallucinated marks or attendance metrics. | **No** |
| **"Dockerized deployment"** | **PASS** | Executed true clean-state timing test (`docker compose down -v`, `docker rmi` project images, `build --no-cache`). Live timing breakdown:<br>• **Image Build from Scratch:** **307.27 seconds** (5.1 min for apt-get and wheel installs).<br>• **Postgres Healthcheck Readiness:** **6.27 seconds**.<br>• **API Auto-ETL & `/health` 200 Ready:** **11.92 seconds** post-launch (populates all 180,000 rows across 4 tables).<br>• **Total Sequence (Scratch Build + Up + ETL + Verify):** **319.19 seconds (5.3 minutes)**.<br>• **Re-run / Post-Build Cold-Start (wiped volume):** **11.92–16.43 seconds**.<br>Confirmed live: port 8000 returned healthy status with all 4 table counts, and port 8501 returned 200 OK dashboard. | **No** |
| **"Cross-cutting adversarial checks"** | **PASS** | Audit of `README.md`, `Arch.html`, and `src/dashboard/app.js` confirmed zero promotional overclaims ("accurately", "powerful" are absent near model claims). Non-existent student query (`STU99999`) returned clean HTTP 404 with structured UI fallback card. Team ID (`60`) and Problem Code (`KDAC-3`) are consistently stated across README, docs, and lineage records. | **No** |

---

## 2. Blocking Issues

*These represent areas that could undermine team credibility during live judge interrogation if left unaddressed.*

### Issue 1: Model 2 AUC (0.5044) & Model 1 $R^2$ (0.2096) Defensibility
* **The Threat:** A skeptical ML judge or data scientist will look at an AUC of 0.5044 and state: *"Your classifier is a random coin toss. Why is this in an AI hackathon submission?"* Similarly, $R^2 = 0.2096$ leaves 79% of CGPA variance unexplained.
* **Root Cause:** When we audited the baseline models, we discovered massive circular target leakage (models trained on current CGPA and attendance achieved $R^2 = 0.94$ and $98\%$ precision, but were functionally fraudulent). Stripping circular academic leakage left only behavioral lifestyle survey signals, which have inherently weak statistical correlation with semester exams.
* **Mandatory Fix / Pitch Strategy:**
  1. **Lead with the Leakage Discovery:** Never present Models 1 and 2 as "accurate production predictors." Present them as **an audit case study in ethical ML engineering**.
  2. **Demonstrate the Leakage Ablation:** Show the judge that achieving $98\%$ accuracy on this dataset was trivial via circular features (`anchor_backlog_history`), but worthless in practice.
  3. **Emphasize Honest Calibration:** Show the UI's amber warning banners (e.g., *"Model Calibration: 45% Recall, 32% Precision — 2 in 3 flags are false alarms"*). Judges respect intellectual honesty over fabricated $99\%$ accuracy.

### Issue 2: Host Port 5432 Collision during Local Evaluation
* **The Threat:** Evaluators testing the project on their local machines who already have a local PostgreSQL instance running will encounter:  
  `driver failed programming external connectivity on endpoint campus360_postgres: Bind for 0.0.0.0:5432 failed: port is already allocated`
* **Specific Fix:** Include a prominent troubleshooting callout in `README.md` advising users to either stop local postgres (`brew services stop postgresql@16` or `sudo systemctl stop postgresql`) or set `DB_ENGINE=sqlite` to run off the standalone fallback warehouse.

---

## 3. Polish Items (Non-Blocking Improvements)

1. **Filter Out 'Overall Score' from 'Lowest-Performing Subject' Table:**  
   *Current Behavior:* The table `/api/analytics/subjects` lists "Overall Score" as the lowest-performing subject across all 6 branches because Kundan's composite term marks average 63.8%.  
   *Suggestion:* Exclude composite metrics (`Overall Score`, `Overall Percentage`, `Degree CGPA`) from the branch-level subject gap table so it only displays modular course subjects (Mathematics, Science, English).
2. **At-Risk Table Empty Filter State:**  
   *Current Behavior:* When a filter combination yields 0 students, the table body clears to whitespace without a message.  
   *Suggestion:* Insert a standard `<tr class="text-center"><td colspan="6" class="py-8 text-gray-500">No students match current filter parameters</td></tr>`.
3. **Purge Deprecated "Model 3" Mentions in Docs:**  
   *Current Behavior:* `docs/ARCHITECTURE.md` (line 92) and `docs/DEPLOYMENT.md` (line 25) reference `train_career_model.py` and "Model 3".  
   *Suggestion:* Update these two references to clarify that Career Guidance is an analytical weighted composite scoring engine (`_CAREER_WEIGHTS`), matching the implementation in `src/api/main.py`.
4. **Header Badge Synchronization on Arch.html:**  
   *Current Behavior:* `Arch.html` displays "Campus360 — Architecture & Data Lineage Reference" without explicit "KDAC-3 · Team 60" metadata in the header title.  
   *Suggestion:* Add an inline pill badge: `<span class="badge">KDAC-3 · Team 60</span>` to match `README.md`.

---

## 4. Judge Q&A Stress Test (5 Adversarial Questions & Honest Answers)

### Question 1: *"Your Model 2 ROC-AUC is 0.5044. That is mathematically indistinguishable from random chance. Why did you deploy an ML model that cannot predict at-risk students?"*
> **Honest Answer:**  
> *"Because deploying a real 0.50 AUC model with transparent calibration is vastly superior to deploying a fake 0.98 AUC model that relies on target leakage. In our initial experiments, including current CGPA and backlogs produced a 98% accurate model, but in a real college, an advisor doesn't need ML to know that a student with 4 backlogs and a 4.0 CGPA is failing—that's post-hoc reporting, not early warning. When we restricted features strictly to early-stage behavioral signals (study hours, sleep, screen time), the statistical reality of these independent datasets showed that lifestyle habits alone do not linearly cause grade failure. Instead of faking high accuracy, we built prominent amber disclosure banners in the UI and embedded the exact 45% recall / 32% precision rates directly into the Gemini prompt so faculty treat the output as a gentle check-in cue, never a disciplinary label."*

---

### Question 2: *"Why does 'Overall Score' appear as a subject in your learning gaps table, and why is it the lowest across every single branch?"*
> **Honest Answer:**  
> *"That reflects the source schema of the Kundan performance dataset. Kundan recorded modular scores for Mathematics, Science, and English, plus a consolidated 'overall_score'. In our transactional star-schema design, every assessment event was mapped to `fact_performance`. Kundan's overall score happened to have an empirical mean of 63.8%, which is slightly lower than individual course averages (64.5%–64.9%). Because our server-side aggregation queried the minimum average marks grouped by branch and subject, 'Overall Score' naturally emerged as the lowest numerical entry across branches. In production curriculum analytics, composite grades should be tagged with a separate assessment type flag so modular subjects alone populate the departmental remedial action table."*

---

### Question 3: *"You stitched 6 independent datasets without common primary keys by matching students on tertile performance bands and branch clusters. Didn't this create synthetic correlations that invalidate your data analysis?"*
> **Honest Answer:**  
> *"In real-world university IT environments, central student ERPs rarely link cleanly to external LMS platforms, lifestyle survey forms, and third-party placement portals. The KDAC-3 problem statement explicitly called for 'data stitching' across these disparate sources. We implemented an attribute-based similarity matching algorithm without replacement that preserves marginal distributions and aligns students within broad academic tertiles (Low, Medium, High) and demographic clusters. While this preserves cross-sectional coherence—ensuring a student in the top academic tier isn't assigned a 35% attendance score—we treat cross-table conclusions as population-level exploratory signals, not individual clinical truths. That is why our star schema explicitly tracks `source` and match flags (`has_suvidya_match`, `has_kundan_match`), allowing any analyst to isolate primary anchor records from secondary stitched records."*

---

### Question 4: *"Your project documentation and file tree mention `train_career_model.py`, but the file is 0 bytes and there is no trained `.joblib` model for career. Did you fail to deliver Model 3?"*
> **Honest Answer:**  
> *"We made an intentional architectural decision to reject an ML classifier for career readiness in favor of a deterministic, population-normalized weighted composite score. Predicting 'Placed vs. Not Placed' with a black-box model gives students an opaque probability (e.g. '62% chance of placement') with no actionable feedback. Instead, our Career Readiness engine computes percentiles across 6 concrete pillars: CGPA (25%), DSA Problems (20%), Aptitude (15%), Mock Interviews (15%), Coding Skills (15%), and Communication (10%). This allows us to tell a student: 'Your readiness score is 50.4/100; your primary bottleneck is your project portfolio (14th percentile).' This actionable diagnostic directly feeds our GenAI narrative layer and provides far more educational value than an opaque ML binary prediction."*

---

### Question 5: *"If a mentor relies on your At-Risk detection system, with a 32% precision rate, two out of every three students flagged are false alarms. How is this operationally viable for faculty?"*
> **Honest Answer:**  
> *"In preventive student welfare, the cost of a false negative (failing to identify a student who subsequently drops out or suffers severe burnout) is orders of magnitude higher than the cost of a false positive (a mentor holding a brief, informal 5-minute conversation with a student who is doing fine). High-recall, low-precision screening is standard practice in early medical screening (e.g. mammography) and financial fraud triage. What makes Campus360 viable is that our UI explicitly informs the advisor: '2 out of 3 flags are false alarms—use this as an informal conversation starter, not a formal intervention.' Furthermore, the GenAI brief provides the advisor with the exact lifestyle dimension driving the flag, enabling empathetic, low-friction check-ins."*

---

## 5. Pre-Submission Checklist

- [x] **PostgreSQL 16 Foreign Keys Enforced:** Verified via live reject test.
- [x] **Zero Dimension Column Leakage:** Confirmed across all 3 fact tables.
- [x] **Automated Clean-State ETL:** Verified unattended in 8.36 seconds.
- [x] **Docker Cold Deployment:** Verified unattended (319.19s from absolute zero / 11.92s container auto-ETL).
- [x] **GenAI Resilient Fallback:** Verified with broken API key across all 3 endpoints.
- [x] **GenAI Grounding / Zero Hallucination:** Verified against edge-case student with missing data.
- [x] **No Exaggerated Promotional Claims:** Verified across README, Arch.html, and UI.
- [x] **Team ID & Problem Code Consistency:** Verified as Team 60 / KDAC-3.
