# SSC CGL Previous Year Papers & Mock Test Portal

A modern, responsive full-stack web application designed for SSC CGL aspirants to practice official previous-year papers and curated model papers in an interactive examination interface.

---

## 🌟 Key Features

1. **Interactive Examination Interface**
   - One question at a time with clear, legible typography.
   - Question palette with status indicators (Attempted, Unattempted, Marked for Review, Current, Remaining).
   - Real-time countdown timer with visual alerts under 5 minutes.
   - **Immediate Answer Checking (Section 8)**: Click "Submit Answer" on any question to instantly reveal whether the answer is **✅ Correct (Green)** or **❌ Wrong (Red)**, showing your chosen answer, official correct answer, and detailed step-by-step solutions (Blue Information box). Locks re-submission per question.
   - Question navigation: Previous, Next, Clear Answer, Mark for Review, Jump to any question from palette.
   - Full test completion confirmation modal with auto-submit on timer expiry.

2. **Year-Wise & Shift-Wise Papers Archive**
   - Categorized by year (2025 Model, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016).
   - Multiple shifts per year (Tier 1 – Shift 1, Shift 2, Shift 3).
   - Clear provenance badges (**Official Verified PYQ**, **Model Paper**, **Practice Test**) to preserve content integrity (Section 19).

3. **Configurable Scoring & Negative Marking**
   - Configurable per paper (Default: **+2.0 Marks** for Correct, **-0.50 Marks** Negative Marking).
   - Automatically computes: Positive marks, Negative deductions, Net Score, Percentage, and Accuracy %.

4. **Detailed Scorecard & Performance Analytics**
   - Automated performance grade feedback:
     - **90%+** → *Excellent*
     - **75–89%** → *Very Good*
     - **60–74%** → *Good*
     - **40–59%** → *Needs Improvement*
     - **Below 40%** → *Keep Practicing*
   - Subject-wise accuracy and score cards covering all 4 SSC CGL sections:
     - General Intelligence & Reasoning
     - General Awareness
     - Quantitative Aptitude
     - English Comprehension
   - Interactive charts (Score progression line chart, Correct vs Wrong doughnut chart) via Chart.js.

5. **Detailed Question-by-Question Review**
   - Filters: *All*, *Correct*, *Wrong*, *Unanswered*.
   - Displays candidate selection, official correct answer key, and in-depth explanation.

6. **My Results (Attempt History)**
   - Complete historical log of tests taken with date, score, %, correct/wrong counts, and time taken.
   - Quick actions: *View Result*, *Review Answers*, *Retake Mock*.

7. **Secure Authentication & Role-Based Access**
   - Password hashing using Werkzeug `generate_password_hash` (scrypt / pbkdf2).
   - Role-based authorization (`user` vs `admin`).
   - Protected routes and session safeguards.

8. **Comprehensive Admin Dashboard**
   - Manage Papers and Shifts (Add, Edit, Delete, configure duration and marks).
   - Convenient question-entry form (Question, Options A-D, Correct answer, Subject, Topic, Difficulty, Explanation).
   - **Bulk Question Import**: Upload questions via JSON or CSV files.
   - **Question Export**: Download question bank in JSON or CSV.
   - User Directory with attempt metrics.

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10+
- Flask & Werkzeug (pre-installed)
- SQLite3 (built-in standard library)

### 2. Run the Application
Open a terminal in the project directory:
```bash
cd C:\Users\mutch\.gemini\antigravity\scratch\ssc-cgl-portal
python app.py
```
Open your browser at:
`http://127.0.0.1:5000`

### 3. Demo Credentials
| Role | Username / Email | Password | Access |
|---|---|---|---|
| **Aspirant** | `aspirant` / `aspirant@ssccgl.org` | `aspirant123` | Dashboard, Tests, Results, Review, Analytics |
| **Admin** | `admin` / `admin@ssccgl.org` | `admin123` | Full Admin Panel, Papers, Questions, Bulk Import |

---

## 🗄️ Database Architecture

- **`users`**: Candidate accounts, roles (`user`, `admin`), password hashes, target year.
- **`papers`**: Year-wise examination papers, shifts, duration, marking schemes (+2 / -0.50), provenance types.
- **`subjects`**: 4 core SSC CGL sections (GI, GA, QA, EC).
- **`questions`**: Question statements, options (A, B, C, D), correct option, step-by-step explanations, topic, difficulty.
- **`test_attempts`**: Session scores, start/end timestamps, net marks, percentage, accuracy, time taken.
- **`user_answers`**: Selected options, is_correct flags, review flags, submission status, time spent.

---

## 🧪 Automated Test Suite
Run the full test suite verifying authentication, immediate answer checking, scoring formulas, and admin operations:
```bash
python -m unittest test_app.py
```
