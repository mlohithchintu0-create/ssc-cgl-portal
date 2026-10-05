import os
import json
import csv
import io
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, abort, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ssc-cgl-portal-super-secret-key-2025-secure')
app.config['JSON_SORT_KEYS'] = False

# -------------------------------------------------------------
# Authentication & Authorization Helpers
# -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin authorization required. Please log in.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, full_name FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
    return dict(current_user=user, current_year=datetime.now().year)

# -------------------------------------------------------------
# Auth Routes
# -------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM papers")
    total_papers = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM questions")
    total_questions = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM test_attempts WHERE status = 'completed'")
    total_tests_taken = cursor.fetchone()['count']
    conn.close()
    return render_template('index.html', total_papers=total_papers, total_questions=total_questions, total_tests_taken=total_tests_taken)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        target_year = request.form.get('target_year', 2025)

        if not full_name or not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('signup.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('signup.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            flash('Username or email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        password_hash = generate_password_hash(password)
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role, full_name, target_year)
        VALUES (?, ?, ?, 'user', ?, ?)
        """, (username, email, password_hash, full_name, target_year))
        conn.commit()

        user_id = cursor.lastrowid
        conn.close()

        # Log user in
        session['user_id'] = user_id
        session['username'] = username
        session['role'] = 'user'
        session['full_name'] = full_name
        flash(f'Account created successfully! Welcome to SSC CGL Mock Portal, {full_name}.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        if not login_id or not password:
            flash('Please enter your username/email and password.', 'danger')
            return render_template('login.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
        """, (login_id, login_id))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# -------------------------------------------------------------
# User Dashboard
# -------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    # User overall statistics
    cursor.execute("""
    SELECT 
        COUNT(*) as total_attempts,
        COALESCE(SUM(attempted_questions), 0) as total_questions_attempted,
        COALESCE(SUM(correct_answers), 0) as total_correct,
        COALESCE(SUM(wrong_answers), 0) as total_wrong,
        COALESCE(AVG(percentage), 0.0) as average_percentage,
        COALESCE(MAX(final_score), 0.0) as best_score,
        COALESCE(SUM(final_score), 0.0) as overall_score
    FROM test_attempts 
    WHERE user_id = ? AND status = 'completed'
    """, (user_id,))
    stats = cursor.fetchone()

    # Recent test attempts
    cursor.execute("""
    SELECT 
        ta.id, ta.paper_id, ta.start_time, ta.end_time, ta.final_score, ta.max_marks,
        ta.percentage, ta.accuracy, ta.total_questions, ta.correct_answers, ta.wrong_answers,
        p.title as paper_title, p.year, p.tier, p.shift, p.paper_type
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.user_id = ? AND ta.status = 'completed'
    ORDER BY ta.start_time DESC
    LIMIT 5
    """, (user_id,))
    recent_attempts = cursor.fetchall()

    # Subject-wise breakdown for user
    cursor.execute("""
    SELECT 
        s.name as subject_name,
        s.code as subject_code,
        COUNT(ua.id) as total_subject_questions,
        COALESCE(SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END), 0) as subject_correct,
        COALESCE(SUM(CASE WHEN ua.is_correct = 0 THEN 1 ELSE 0 END), 0) as subject_wrong
    FROM user_answers ua
    JOIN test_attempts ta ON ua.attempt_id = ta.id
    JOIN questions q ON ua.question_id = q.id
    JOIN subjects s ON q.subject_id = s.id
    WHERE ta.user_id = ? AND ta.status = 'completed' AND ua.is_submitted = 1
    GROUP BY s.id
    ORDER BY s.id
    """, (user_id,))
    subject_stats = cursor.fetchall()

    # Available years for quick paper selection
    cursor.execute("""
    SELECT DISTINCT year, COUNT(*) as paper_count 
    FROM papers 
    WHERE is_active = 1 
    GROUP BY year 
    ORDER BY year DESC
    """)
    years_summary = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_attempts=recent_attempts,
        subject_stats=subject_stats,
        years_summary=years_summary
    )

# -------------------------------------------------------------
# Year-Wise Previous Papers & Paper Info
# -------------------------------------------------------------
@app.route('/papers')
@login_required
def papers():
    year_filter = request.args.get('year', type=int)
    type_filter = request.args.get('type')
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT 
        p.*,
        COUNT(q.id) as actual_question_count
    FROM papers p
    LEFT JOIN questions q ON p.id = q.paper_id
    WHERE p.is_active = 1
    """
    params = []

    if year_filter:
        query += " AND p.year = ?"
        params.append(year_filter)
    if type_filter:
        query += " AND p.paper_type = ?"
        params.append(type_filter)

    query += " GROUP BY p.id ORDER BY p.year DESC, p.title ASC"

    cursor.execute(query, params)
    all_papers = cursor.fetchall()

    # Group papers year-wise
    grouped_papers = {}
    for p in all_papers:
        yr = p['year']
        if yr not in grouped_papers:
            grouped_papers[yr] = []
        grouped_papers[yr].append(p)

    # Distinct years for tabs/filters
    cursor.execute("SELECT DISTINCT year FROM papers WHERE is_active = 1 ORDER BY year DESC")
    available_years = [row['year'] for row in cursor.fetchall()]

    conn.close()
    return render_template(
        'papers.html',
        grouped_papers=grouped_papers,
        available_years=available_years,
        selected_year=year_filter,
        selected_type=type_filter
    )

@app.route('/papers/<int:paper_id>')
@login_required
def paper_detail(paper_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        p.*,
        COUNT(q.id) as question_count
    FROM papers p
    LEFT JOIN questions q ON p.id = q.paper_id
    WHERE p.id = ?
    GROUP BY p.id
    """, (paper_id,))
    paper = cursor.fetchone()

    if not paper:
        conn.close()
        flash('Question paper not found.', 'danger')
        return redirect(url_for('papers'))

    # Subject breakdown for this paper
    cursor.execute("""
    SELECT 
        s.name as subject_name,
        COUNT(q.id) as count
    FROM questions q
    JOIN subjects s ON q.subject_id = s.id
    WHERE q.paper_id = ?
    GROUP BY s.id
    ORDER BY s.id
    """, (paper_id,))
    subject_distribution = cursor.fetchall()

    # Check if user already has an in-progress or past attempt
    cursor.execute("""
    SELECT id, status, final_score, max_marks, percentage 
    FROM test_attempts 
    WHERE user_id = ? AND paper_id = ? 
    ORDER BY start_time DESC LIMIT 1
    """, (session['user_id'], paper_id))
    last_attempt = cursor.fetchone()

    conn.close()

    max_marks = (paper['question_count'] or 0) * paper['marks_per_question']

    return render_template(
        'paper_detail.html',
        paper=paper,
        subject_distribution=subject_distribution,
        last_attempt=last_attempt,
        max_marks=max_marks
    )

# -------------------------------------------------------------
# Mock Test Engine & Examination Interface
# -------------------------------------------------------------
@app.route('/test/<int:paper_id>')
@login_required
def take_test(paper_id):
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM papers WHERE id = ? AND is_active = 1", (paper_id,))
    paper = cursor.fetchone()
    if not paper:
        conn.close()
        flash('Exam paper not found or inactive.', 'danger')
        return redirect(url_for('papers'))

    # Check for active in-progress attempt
    cursor.execute("""
    SELECT * FROM test_attempts 
    WHERE user_id = ? AND paper_id = ? AND status = 'in_progress'
    ORDER BY start_time DESC LIMIT 1
    """, (user_id, paper_id))
    attempt = cursor.fetchone()

    # If no in-progress attempt, create one
    if not attempt:
        cursor.execute("SELECT COUNT(*) as cnt FROM questions WHERE paper_id = ?", (paper_id,))
        q_count = cursor.fetchone()['cnt']

        if q_count == 0:
            conn.close()
            flash('This paper does not contain any questions yet. Please choose another paper or contact admin.', 'warning')
            return redirect(url_for('paper_detail', paper_id=paper_id))

        max_marks = q_count * paper['marks_per_question']

        cursor.execute("""
        INSERT INTO test_attempts 
        (user_id, paper_id, status, total_questions, max_marks, start_time)
        VALUES (?, ?, 'in_progress', ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, paper_id, q_count, max_marks))
        conn.commit()
        attempt_id = cursor.lastrowid

        # Initialize user_answers rows for all questions in this paper
        cursor.execute("SELECT id FROM questions WHERE paper_id = ? ORDER BY order_num ASC, id ASC", (paper_id,))
        all_q = cursor.fetchall()
        for q in all_q:
            cursor.execute("""
            INSERT INTO user_answers (attempt_id, question_id)
            VALUES (?, ?)
            """, (attempt_id, q['id']))
        conn.commit()

        cursor.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        attempt = cursor.fetchone()

    conn.close()
    return render_template('test.html', paper=paper, attempt=attempt)

# API Endpoint to fetch test state
@app.route('/api/attempt/<int:attempt_id>/state')
@login_required
def api_attempt_state(attempt_id):
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ta.*, p.title as paper_title, p.duration_minutes, p.marks_per_question, p.negative_marks, p.paper_type
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.id = ? AND ta.user_id = ?
    """, (attempt_id, user_id))
    attempt = cursor.fetchone()

    if not attempt:
        conn.close()
        return jsonify({'error': 'Attempt not found'}), 404

    # Fetch questions with user answers
    cursor.execute("""
    SELECT 
        q.id, q.order_num, q.question_text, q.question_image,
        q.option_a, q.option_b, q.option_c, q.option_d,
        q.difficulty, q.topic, q.question_type,
        s.name as subject_name, s.code as subject_code,
        ua.selected_option, ua.is_marked_for_review, ua.is_submitted,
        ua.is_correct, ua.time_spent_seconds,
        CASE WHEN ua.is_submitted = 1 OR ta.status = 'completed' THEN q.correct_option ELSE NULL END as correct_option,
        CASE WHEN ua.is_submitted = 1 OR ta.status = 'completed' THEN q.explanation ELSE NULL END as explanation
    FROM questions q
    JOIN subjects s ON q.subject_id = s.id
    JOIN user_answers ua ON ua.question_id = q.id AND ua.attempt_id = ?
    JOIN test_attempts ta ON ta.id = ua.attempt_id
    WHERE q.paper_id = ?
    ORDER BY q.order_num ASC, q.id ASC
    """, (attempt_id, attempt['paper_id']))
    questions = cursor.fetchall()

    questions_list = []
    for q in questions:
        questions_list.append(dict(q))

    # Calculate remaining time in seconds
    # If duration is 60 mins, end time is start_time + 60 mins
    cursor.execute("SELECT strftime('%s', 'now') - strftime('%s', start_time) as elapsed_seconds FROM test_attempts WHERE id = ?", (attempt_id,))
    elapsed = cursor.fetchone()['elapsed_seconds'] or 0
    total_seconds = attempt['duration_minutes'] * 60
    remaining_seconds = max(0, total_seconds - elapsed)

    conn.close()
    return jsonify({
        'attempt': dict(attempt),
        'remaining_seconds': remaining_seconds,
        'questions': questions_list
    })

# API Endpoint to submit answer for a single question (Immediate Feedback mode)
@app.route('/api/attempt/<int:attempt_id>/submit_answer', methods=['POST'])
@login_required
def api_submit_answer(attempt_id):
    user_id = session['user_id']
    data = request.get_json() or {}
    question_id = data.get('question_id')
    selected_option = data.get('selected_option') # 'A', 'B', 'C', 'D'
    time_spent = data.get('time_spent_seconds', 0)

    if not question_id or not selected_option:
        return jsonify({'error': 'Missing question ID or selected option'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Verify attempt ownership & status
    cursor.execute("""
    SELECT ta.status, q.correct_option, q.explanation
    FROM test_attempts ta
    JOIN questions q ON q.id = ?
    WHERE ta.id = ? AND ta.user_id = ?
    """, (question_id, attempt_id, user_id))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Question or attempt not found'}), 404

    if row['status'] != 'in_progress':
        conn.close()
        return jsonify({'error': 'Test is already completed'}), 400

    correct_option = row['correct_option']
    explanation = row['explanation']
    is_correct = 1 if selected_option.upper() == correct_option.upper() else 0

    # Update user answer
    cursor.execute("""
    UPDATE user_answers
    SET selected_option = ?,
        is_correct = ?,
        is_submitted = 1,
        time_spent_seconds = time_spent_seconds + ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE attempt_id = ? AND question_id = ?
    """, (selected_option.upper(), is_correct, time_spent, attempt_id, question_id))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'is_correct': bool(is_correct),
        'selected_option': selected_option.upper(),
        'correct_option': correct_option,
        'explanation': explanation
    })

# API Endpoint to save state (clear, mark review, select option without immediate check)
@app.route('/api/attempt/<int:attempt_id>/update_state', methods=['POST'])
@login_required
def api_update_state(attempt_id):
    user_id = session['user_id']
    data = request.get_json() or {}
    question_id = data.get('question_id')
    selected_option = data.get('selected_option') # 'A', 'B', 'C', 'D', or null
    is_marked_for_review = 1 if data.get('is_marked_for_review') else 0
    current_index = data.get('current_index', 0)
    time_spent = data.get('time_spent_seconds', 0)

    conn = get_db()
    cursor = conn.cursor()

    # Verify attempt ownership & status
    cursor.execute("SELECT status FROM test_attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id))
    att = cursor.fetchone()
    if not att or att['status'] != 'in_progress':
        conn.close()
        return jsonify({'error': 'Attempt not found or closed'}), 400

    if question_id:
        # Check if already submitted
        cursor.execute("SELECT is_submitted, correct_option FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.attempt_id = ? AND ua.question_id = ?", (attempt_id, question_id))
        ans = cursor.fetchone()

        if ans and ans['is_submitted'] == 1:
            # If already submitted, only allow toggling review flag
            cursor.execute("""
            UPDATE user_answers 
            SET is_marked_for_review = ?,
                time_spent_seconds = time_spent_seconds + ?
            WHERE attempt_id = ? AND question_id = ?
            """, (is_marked_for_review, time_spent, attempt_id, question_id))
        else:
            is_correct = None
            if selected_option and ans:
                is_correct = 1 if selected_option.upper() == ans['correct_option'] else 0

            cursor.execute("""
            UPDATE user_answers 
            SET selected_option = ?,
                is_correct = ?,
                is_marked_for_review = ?,
                time_spent_seconds = time_spent_seconds + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE attempt_id = ? AND question_id = ?
            """, (selected_option, is_correct, is_marked_for_review, time_spent, attempt_id, question_id))

    cursor.execute("""
    UPDATE test_attempts 
    SET current_question_index = ? 
    WHERE id = ?
    """, (current_index, attempt_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

# API Endpoint to finish test and calculate all scores
@app.route('/api/attempt/<int:attempt_id>/finish', methods=['POST'])
@login_required
def api_finish_test(attempt_id):
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ta.*, p.marks_per_question, p.negative_marks
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.id = ? AND ta.user_id = ?
    """, (attempt_id, user_id))
    attempt = cursor.fetchone()

    if not attempt:
        conn.close()
        return jsonify({'error': 'Attempt not found'}), 404

    if attempt['status'] == 'completed':
        conn.close()
        return jsonify({'redirect': url_for('test_result', attempt_id=attempt_id)})

    marks_per_q = attempt['marks_per_question']
    negative_marks_per_q = attempt['negative_marks']

    # Get all answers and questions for calculation
    cursor.execute("""
    SELECT 
        ua.id, ua.selected_option, ua.is_submitted,
        q.correct_option
    FROM user_answers ua
    JOIN questions q ON ua.question_id = q.id
    WHERE ua.attempt_id = ?
    """, (attempt_id,))
    answers = cursor.fetchall()

    total_questions = len(answers)
    attempted_questions = 0
    correct_answers = 0
    wrong_answers = 0
    unanswered_questions = 0

    for ans in answers:
        sel = ans['selected_option']
        if sel:
            attempted_questions += 1
            if sel.upper() == ans['correct_option'].upper():
                correct_answers += 1
                cursor.execute("UPDATE user_answers SET is_correct = 1, is_submitted = 1 WHERE id = ?", (ans['id'],))
            else:
                wrong_answers += 1
                cursor.execute("UPDATE user_answers SET is_correct = 0, is_submitted = 1 WHERE id = ?", (ans['id'],))
        else:
            unanswered_questions += 1
            cursor.execute("UPDATE user_answers SET is_correct = NULL WHERE id = ?", (ans['id'],))

    positive_marks = correct_answers * marks_per_q
    negative_marks = wrong_answers * negative_marks_per_q
    final_score = max(0.0, round(positive_marks - negative_marks, 2))
    max_marks = total_questions * marks_per_q
    percentage = round((final_score / max_marks * 100), 2) if max_marks > 0 else 0.0
    accuracy = round((correct_answers / attempted_questions * 100), 2) if attempted_questions > 0 else 0.0

    # Calculate actual time taken
    cursor.execute("SELECT strftime('%s', 'now') - strftime('%s', start_time) as time_diff FROM test_attempts WHERE id = ?", (attempt_id,))
    time_taken = cursor.fetchone()['time_diff'] or 0

    cursor.execute("""
    UPDATE test_attempts
    SET status = 'completed',
        end_time = CURRENT_TIMESTAMP,
        total_questions = ?,
        attempted_questions = ?,
        correct_answers = ?,
        wrong_answers = ?,
        unanswered_questions = ?,
        positive_marks = ?,
        negative_marks = ?,
        final_score = ?,
        max_marks = ?,
        percentage = ?,
        accuracy = ?,
        time_taken_seconds = ?
    WHERE id = ?
    """, (
        total_questions, attempted_questions, correct_answers, wrong_answers,
        unanswered_questions, positive_marks, negative_marks, final_score,
        max_marks, percentage, accuracy, time_taken, attempt_id
    ))

    conn.commit()
    conn.close()

    return jsonify({'redirect': url_for('test_result', attempt_id=attempt_id)})

# -------------------------------------------------------------
# Result Page
# -------------------------------------------------------------
@app.route('/result/<int:attempt_id>')
@login_required
def test_result(attempt_id):
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        ta.*,
        p.title as paper_title, p.exam_name, p.year, p.tier, p.shift,
        p.marks_per_question, p.negative_marks, p.paper_type
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.id = ? AND (ta.user_id = ? OR ? = 'admin')
    """, (attempt_id, user_id, session.get('role')))
    attempt = cursor.fetchone()

    if not attempt:
        conn.close()
        flash('Result not found or access unauthorized.', 'danger')
        return redirect(url_for('dashboard'))

    # Average time per question
    attempted = attempt['attempted_questions'] or 0
    time_taken = attempt['time_taken_seconds'] or 0
    avg_time_per_q = round(time_taken / attempted) if attempted > 0 else 0

    # Performance tier feedback
    pct = attempt['percentage']
    if pct >= 90:
        perf_tier = 'Excellent'
        perf_message = 'Outstanding performance! You are performing in the top percentile for SSC CGL. Keep maintaining your accuracy.'
        perf_badge_color = 'emerald'
    elif pct >= 75:
        perf_tier = 'Very Good'
        perf_message = 'Great effort! You have a solid grasp of core concepts. Fine-tune your time management to reach the 90%+ bracket.'
        perf_badge_color = 'blue'
    elif pct >= 60:
        perf_tier = 'Good'
        perf_message = 'Satisfactory performance. You cleared the qualifying cut-off benchmark, but need to reduce negative marks.'
        perf_badge_color = 'indigo'
    elif pct >= 40:
        perf_tier = 'Needs Improvement'
        perf_message = 'You need more targeted practice. Focus on weak subjects and avoid speculative guessing to prevent penalties.'
        perf_badge_color = 'amber'
    else:
        perf_tier = 'Keep Practicing'
        perf_message = 'Fundamental revision required. Review formulas, vocabulary, and shortcuts, then retake this mock.'
        perf_badge_color = 'rose'

    # Subject-wise breakdown for this attempt
    cursor.execute("""
    SELECT 
        s.name as subject_name,
        s.code as subject_code,
        COUNT(q.id) as total_questions,
        COALESCE(SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END), 0) as correct_count,
        COALESCE(SUM(CASE WHEN ua.is_correct = 0 THEN 1 ELSE 0 END), 0) as wrong_count,
        COALESCE(SUM(CASE WHEN ua.selected_option IS NULL THEN 1 ELSE 0 END), 0) as unanswered_count
    FROM questions q
    JOIN subjects s ON q.subject_id = s.id
    JOIN user_answers ua ON ua.question_id = q.id AND ua.attempt_id = ?
    WHERE q.paper_id = ?
    GROUP BY s.id
    ORDER BY s.id
    """, (attempt_id, attempt['paper_id']))
    subject_results = cursor.fetchall()

    conn.close()

    return render_template(
        'result.html',
        attempt=attempt,
        avg_time_per_q=avg_time_per_q,
        perf_tier=perf_tier,
        perf_message=perf_message,
        perf_badge_color=perf_badge_color,
        subject_results=subject_results
    )

# -------------------------------------------------------------
# Detailed Answer Review
# -------------------------------------------------------------
@app.route('/review/<int:attempt_id>')
@login_required
def test_review(attempt_id):
    user_id = session['user_id']
    filter_status = request.args.get('filter', 'all') # all, correct, wrong, unanswered
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        ta.*,
        p.title as paper_title, p.exam_name, p.year, p.tier, p.shift, p.paper_type
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.id = ? AND (ta.user_id = ? OR ? = 'admin')
    """, (attempt_id, user_id, session.get('role')))
    attempt = cursor.fetchone()

    if not attempt:
        conn.close()
        flash('Attempt not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Fetch all questions with user's answers and explanations
    cursor.execute("""
    SELECT 
        q.*,
        s.name as subject_name,
        ua.selected_option,
        ua.is_correct,
        ua.is_marked_for_review,
        ua.time_spent_seconds
    FROM questions q
    JOIN subjects s ON q.subject_id = s.id
    JOIN user_answers ua ON ua.question_id = q.id AND ua.attempt_id = ?
    WHERE q.paper_id = ?
    ORDER BY q.order_num ASC, q.id ASC
    """, (attempt_id, attempt['paper_id']))
    all_questions = cursor.fetchall()

    filtered_questions = []
    for q in all_questions:
        status = 'unanswered'
        if q['selected_option']:
            status = 'correct' if q['is_correct'] == 1 else 'wrong'

        if filter_status == 'all' or filter_status == status:
            q_dict = dict(q)
            q_dict['status'] = status
            filtered_questions.append(q_dict)

    conn.close()
    return render_template(
        'review.html',
        attempt=attempt,
        questions=filtered_questions,
        current_filter=filter_status,
        total_count=len(all_questions)
    )

# -------------------------------------------------------------
# Performance Analytics
# -------------------------------------------------------------
@app.route('/analytics')
@login_required
def analytics():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    # Subject-wise overall performance
    cursor.execute("""
    SELECT 
        s.name as subject_name,
        s.code as subject_code,
        COUNT(ua.id) as total_questions,
        COALESCE(SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END), 0) as correct_count,
        COALESCE(SUM(CASE WHEN ua.is_correct = 0 THEN 1 ELSE 0 END), 0) as wrong_count,
        COALESCE(SUM(CASE WHEN ua.selected_option IS NULL THEN 1 ELSE 0 END), 0) as unanswered_count
    FROM user_answers ua
    JOIN test_attempts ta ON ua.attempt_id = ta.id
    JOIN questions q ON ua.question_id = q.id
    JOIN subjects s ON q.subject_id = s.id
    WHERE ta.user_id = ? AND ta.status = 'completed'
    GROUP BY s.id
    ORDER BY s.id
    """, (user_id,))
    subject_stats = cursor.fetchall()

    # Topic-wise performance
    cursor.execute("""
    SELECT 
        s.name as subject_name,
        q.topic,
        COUNT(ua.id) as total_q,
        COALESCE(SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END), 0) as correct_q,
        COALESCE(SUM(CASE WHEN ua.is_correct = 0 THEN 1 ELSE 0 END), 0) as wrong_q
    FROM user_answers ua
    JOIN test_attempts ta ON ua.attempt_id = ta.id
    JOIN questions q ON ua.question_id = q.id
    JOIN subjects s ON q.subject_id = s.id
    WHERE ta.user_id = ? AND ta.status = 'completed'
    GROUP BY s.id, q.topic
    ORDER BY s.id, total_q DESC
    LIMIT 20
    """, (user_id,))
    topic_stats = cursor.fetchall()

    # Score progression across tests
    cursor.execute("""
    SELECT 
        ta.id, ta.start_time, ta.final_score, ta.max_marks, ta.percentage, ta.accuracy,
        p.title as paper_title, p.year
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.user_id = ? AND ta.status = 'completed'
    ORDER BY ta.start_time ASC
    """, (user_id,))
    history = cursor.fetchall()

    # Overall Summary
    cursor.execute("""
    SELECT 
        COUNT(*) as total_tests,
        COALESCE(AVG(final_score), 0.0) as avg_score,
        COALESCE(MAX(final_score), 0.0) as best_score,
        COALESCE(AVG(accuracy), 0.0) as avg_accuracy
    FROM test_attempts 
    WHERE user_id = ? AND status = 'completed'
    """, (user_id,))
    summary = cursor.fetchone()

    conn.close()

    # Identify strong and weak subjects
    strong_subject = None
    weak_subject = None
    highest_acc = -1
    lowest_acc = 101

    for row in subject_stats:
        att = row['correct_count'] + row['wrong_count']
        if att > 0:
            acc = (row['correct_count'] / att) * 100
            if acc > highest_acc:
                highest_acc = acc
                strong_subject = row['subject_name']
            if acc < lowest_acc:
                lowest_acc = acc
                weak_subject = row['subject_name']

    return render_template(
        'analytics.html',
        subject_stats=subject_stats,
        topic_stats=topic_stats,
        history=history,
        summary=summary,
        strong_subject=strong_subject or 'N/A',
        weak_subject=weak_subject or 'N/A'
    )

# -------------------------------------------------------------
# My Results Page
# -------------------------------------------------------------
@app.route('/my-results')
@login_required
def my_results():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        ta.*,
        p.title as paper_title, p.exam_name, p.year, p.tier, p.shift, p.paper_type
    FROM test_attempts ta
    JOIN papers p ON ta.paper_id = p.id
    WHERE ta.user_id = ? AND ta.status = 'completed'
    ORDER BY ta.start_time DESC
    """, (user_id,))
    attempts = cursor.fetchall()

    conn.close()
    return render_template('my_results.html', attempts=attempts)

# -------------------------------------------------------------
# User Profile
# -------------------------------------------------------------
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        target_year = request.form.get('target_year', 2025)
        new_password = request.form.get('new_password', '')

        if full_name:
            if new_password:
                pw_hash = generate_password_hash(new_password)
                cursor.execute("""
                UPDATE users SET full_name = ?, target_year = ?, password_hash = ? WHERE id = ?
                """, (full_name, target_year, pw_hash, user_id))
            else:
                cursor.execute("""
                UPDATE users SET full_name = ?, target_year = ? WHERE id = ?
                """, (full_name, target_year, user_id))
            conn.commit()
            session['full_name'] = full_name
            flash('Profile updated successfully.', 'success')

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
    SELECT 
        COUNT(*) as total_attempts,
        COALESCE(MAX(final_score), 0) as best_score,
        COALESCE(AVG(percentage), 0) as avg_pct
    FROM test_attempts 
    WHERE user_id = ? AND status = 'completed'
    """, (user_id,))
    stats = cursor.fetchone()

    conn.close()
    return render_template('profile.html', user=user, stats=stats)

# -------------------------------------------------------------
# Admin Panel Routes
# -------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM papers")
    total_papers = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM questions")
    total_questions = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'user'")
    total_students = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM test_attempts WHERE status = 'completed'")
    total_attempts = cursor.fetchone()['count']

    cursor.execute("""
    SELECT ta.*, u.full_name as user_name, u.username, p.title as paper_title
    FROM test_attempts ta
    JOIN users u ON ta.user_id = u.id
    JOIN papers p ON ta.paper_id = p.id
    ORDER BY ta.start_time DESC
    LIMIT 8
    """)
    recent_attempts = cursor.fetchall()

    conn.close()
    return render_template(
        'admin/dashboard.html',
        total_papers=total_papers,
        total_questions=total_questions,
        total_students=total_students,
        total_attempts=total_attempts,
        recent_attempts=recent_attempts
    )

@app.route('/admin/papers', methods=['GET', 'POST'])
@admin_required
def admin_papers():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            title = request.form.get('title', '').strip()
            year = request.form.get('year', type=int)
            tier = request.form.get('tier', 'Tier 1')
            shift = request.form.get('shift', 'Shift 1')
            duration = request.form.get('duration_minutes', 60, type=int)
            marks_per_q = request.form.get('marks_per_question', 2.0, type=float)
            neg_marks = request.form.get('negative_marks', 0.50, type=float)
            paper_type = request.form.get('paper_type', 'official_pyq')
            source_attribution = request.form.get('source_attribution', '')
            instructions = request.form.get('instructions', '')

            cursor.execute("""
            INSERT INTO papers 
            (title, exam_name, year, tier, shift, duration_minutes, marks_per_question, negative_marks, paper_type, source_attribution, instructions)
            VALUES (?, 'SSC CGL', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, year, tier, shift, duration, marks_per_q, neg_marks, paper_type, source_attribution, instructions))
            conn.commit()
            conn.close()
            flash(f'Paper "{title}" created successfully.', 'success')
            return redirect(url_for('admin_papers'))

        elif action == 'edit':
            paper_id = request.form.get('paper_id', type=int)
            title = request.form.get('title', '').strip()
            year = request.form.get('year', type=int)
            tier = request.form.get('tier', 'Tier 1')
            shift = request.form.get('shift', 'Shift 1')
            duration = request.form.get('duration_minutes', 60, type=int)
            marks_per_q = request.form.get('marks_per_question', 2.0, type=float)
            neg_marks = request.form.get('negative_marks', 0.50, type=float)
            paper_type = request.form.get('paper_type', 'official_pyq')
            source_attribution = request.form.get('source_attribution', '')
            instructions = request.form.get('instructions', '')

            cursor.execute("""
            UPDATE papers 
            SET title = ?, year = ?, tier = ?, shift = ?, duration_minutes = ?,
                marks_per_question = ?, negative_marks = ?, paper_type = ?,
                source_attribution = ?, instructions = ?
            WHERE id = ?
            """, (title, year, tier, shift, duration, marks_per_q, neg_marks, paper_type, source_attribution, instructions, paper_id))
            conn.commit()
            conn.close()
            flash(f'Paper updated successfully.', 'success')
            return redirect(url_for('admin_papers'))

        elif action == 'delete':
            paper_id = request.form.get('paper_id', type=int)
            cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
            conn.commit()
            conn.close()
            flash('Paper deleted successfully.', 'info')
            return redirect(url_for('admin_papers'))

    cursor.execute("""
    SELECT 
        p.*,
        COUNT(q.id) as question_count
    FROM papers p
    LEFT JOIN questions q ON p.id = q.paper_id
    GROUP BY p.id
    ORDER BY p.year DESC, p.id DESC
    """)
    papers = [dict(p) for p in cursor.fetchall()]
    conn.close()

    return render_template('admin/papers.html', papers=papers)

@app.route('/admin/questions', methods=['GET', 'POST'])
@admin_required
def admin_questions():
    conn = get_db()
    cursor = conn.cursor()

    paper_id_filter = request.args.get('paper_id', type=int)
    subject_id_filter = request.args.get('subject_id', type=int)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            paper_id = request.form.get('paper_id', type=int)
            subject_id = request.form.get('subject_id', type=int)
            topic = request.form.get('topic', '').strip()
            difficulty = request.form.get('difficulty', 'Medium')
            question_text = request.form.get('question_text', '').strip()
            question_image = request.form.get('question_image', '').strip()
            option_a = request.form.get('option_a', '').strip()
            option_b = request.form.get('option_b', '').strip()
            option_c = request.form.get('option_c', '').strip()
            option_d = request.form.get('option_d', '').strip()
            correct_option = request.form.get('correct_option', 'A').upper()
            explanation = request.form.get('explanation', '').strip()
            question_type = request.form.get('question_type', 'official_pyq')
            order_num = request.form.get('order_num', 1, type=int)

            cursor.execute("""
            INSERT INTO questions 
            (paper_id, subject_id, topic, difficulty, question_text, question_image,
             option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id, subject_id, topic, difficulty, question_text, question_image,
                option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num
            ))
            conn.commit()
            conn.close()
            flash('Question added successfully.', 'success')
            return redirect(url_for('admin_questions', paper_id=paper_id))

        elif action == 'edit':
            question_id = request.form.get('question_id', type=int)
            paper_id = request.form.get('paper_id', type=int)
            subject_id = request.form.get('subject_id', type=int)
            topic = request.form.get('topic', '').strip()
            difficulty = request.form.get('difficulty', 'Medium')
            question_text = request.form.get('question_text', '').strip()
            question_image = request.form.get('question_image', '').strip()
            option_a = request.form.get('option_a', '').strip()
            option_b = request.form.get('option_b', '').strip()
            option_c = request.form.get('option_c', '').strip()
            option_d = request.form.get('option_d', '').strip()
            correct_option = request.form.get('correct_option', 'A').upper()
            explanation = request.form.get('explanation', '').strip()
            question_type = request.form.get('question_type', 'official_pyq')
            order_num = request.form.get('order_num', 1, type=int)

            cursor.execute("""
            UPDATE questions 
            SET paper_id = ?, subject_id = ?, topic = ?, difficulty = ?, question_text = ?, question_image = ?,
                option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_option = ?, 
                explanation = ?, question_type = ?, order_num = ?
            WHERE id = ?
            """, (
                paper_id, subject_id, topic, difficulty, question_text, question_image,
                option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num,
                question_id
            ))
            conn.commit()
            conn.close()
            flash('Question updated successfully.', 'success')
            return redirect(url_for('admin_questions', paper_id=paper_id))

        elif action == 'delete':
            question_id = request.form.get('question_id', type=int)
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
            conn.close()
            flash('Question deleted successfully.', 'info')
            return redirect(url_for('admin_questions'))

    # Fetch questions with filter
    q_query = """
    SELECT 
        q.*,
        p.title as paper_title, p.year,
        s.name as subject_name, s.code as subject_code
    FROM questions q
    JOIN papers p ON q.paper_id = p.id
    JOIN subjects s ON q.subject_id = s.id
    WHERE 1=1
    """
    params = []
    if paper_id_filter:
        q_query += " AND q.paper_id = ?"
        params.append(paper_id_filter)
    if subject_id_filter:
        q_query += " AND q.subject_id = ?"
        params.append(subject_id_filter)

    q_query += " ORDER BY q.paper_id DESC, q.order_num ASC, q.id ASC LIMIT 100"

    cursor.execute(q_query, params)
    questions = [dict(q) for q in cursor.fetchall()]

    cursor.execute("SELECT id, title, year FROM papers ORDER BY year DESC, title ASC")
    all_papers = [dict(p) for p in cursor.fetchall()]

    cursor.execute("SELECT id, name, code FROM subjects ORDER BY id ASC")
    all_subjects = [dict(s) for s in cursor.fetchall()]

    conn.close()
    return render_template(
        'admin/questions.html',
        questions=questions,
        all_papers=all_papers,
        all_subjects=all_subjects,
        selected_paper=paper_id_filter,
        selected_subject=subject_id_filter
    )

# Bulk Question Import / Export
@app.route('/admin/questions/import', methods=['POST'])
@admin_required
def admin_questions_import():
    paper_id = request.form.get('target_paper_id', type=int)
    if not paper_id:
        flash('Please select a target paper for import.', 'danger')
        return redirect(url_for('admin_questions'))

    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected for import.', 'danger')
        return redirect(url_for('admin_questions'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, code FROM subjects")
    subject_map = {row['code'].upper(): row['id'] for row in cursor.fetchall()}

    filename = file.filename.lower()
    imported_count = 0

    try:
        if filename.endswith('.json'):
            content = file.read().decode('utf-8')
            items = json.loads(content)
            for item in items:
                sub_code = item.get('subject_code', 'GA').upper()
                sub_id = subject_map.get(sub_code, 1)
                cursor.execute("""
                INSERT INTO questions 
                (paper_id, subject_id, topic, difficulty, question_text, question_image,
                 option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper_id, sub_id, item.get('topic', 'General'), item.get('difficulty', 'Medium'),
                    item['question_text'], item.get('question_image'),
                    item['option_a'], item['option_b'], item['option_c'], item['option_d'],
                    item['correct_option'].upper(), item.get('explanation', ''),
                    item.get('question_type', 'model_question'), item.get('order_num', imported_count + 1)
                ))
                imported_count += 1

        elif filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                sub_code = row.get('subject_code', 'GA').upper()
                sub_id = subject_map.get(sub_code, 1)
                cursor.execute("""
                INSERT INTO questions 
                (paper_id, subject_id, topic, difficulty, question_text, question_image,
                 option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper_id, sub_id, row.get('topic', 'General'), row.get('difficulty', 'Medium'),
                    row['question_text'], row.get('question_image'),
                    row['option_a'], row['option_b'], row['option_c'], row['option_d'],
                    row['correct_option'].upper(), row.get('explanation', ''),
                    row.get('question_type', 'model_question'), int(row.get('order_num', imported_count + 1))
                ))
                imported_count += 1
        else:
            flash('Unsupported file type. Please upload a valid JSON or CSV file.', 'warning')
            conn.close()
            return redirect(url_for('admin_questions'))

        conn.commit()
        flash(f'Successfully imported {imported_count} questions.', 'success')
    except Exception as e:
        flash(f'Error importing file: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('admin_questions', paper_id=paper_id))

@app.route('/admin/questions/export')
@admin_required
def admin_questions_export():
    paper_id = request.args.get('paper_id', type=int)
    fmt = request.args.get('format', 'json')

    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT 
        q.order_num, q.question_text, q.question_image,
        q.option_a, q.option_b, q.option_c, q.option_d,
        q.correct_option, q.explanation, q.topic, q.difficulty, q.question_type,
        s.code as subject_code, s.name as subject_name
    FROM questions q
    JOIN subjects s ON q.subject_id = s.id
    """
    params = []
    if paper_id:
        query += " WHERE q.paper_id = ?"
        params.append(paper_id)

    query += " ORDER BY q.order_num ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    data = [dict(r) for r in rows]

    if fmt == 'csv':
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=ssc_cgl_questions_{paper_id or 'all'}.csv"}
        )
    else:
        return Response(
            json.dumps(data, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=ssc_cgl_questions_{paper_id or 'all'}.json"}
        )

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        u.*,
        COUNT(ta.id) as attempts_count,
        COALESCE(AVG(ta.percentage), 0.0) as avg_percentage,
        COALESCE(MAX(ta.final_score), 0.0) as best_score
    FROM users u
    LEFT JOIN test_attempts ta ON u.id = ta.user_id AND ta.status = 'completed'
    GROUP BY u.id
    ORDER BY u.id ASC
    """)
    users = cursor.fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/deploy', methods=['GET', 'POST'])
@admin_required
def admin_deploy():
    result_msg = None
    is_success = False
    if request.method == 'POST':
        repo_url = request.form.get('repo_url', '').strip()
        token = request.form.get('token', '').strip()

        if not repo_url:
            flash('Please enter your GitHub repository URL.', 'danger')
        else:
            from deploy_push import push_to_remote
            success, msg = push_to_remote(repo_url, token=token)
            is_success = success
            result_msg = msg
            if success:
                flash('Repository pushed to GitHub successfully! Now link it to Render.', 'success')
            else:
                flash(f'Push error: {msg}', 'danger')

    return render_template('admin/deploy.html', result_msg=result_msg, is_success=is_success)

# Auto-initialize database on application startup (works with both Gunicorn and direct python app.py)
with app.app_context():
    try:
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM papers")
        paper_count = cursor.fetchone()['cnt']
        conn.close()
        if paper_count == 0:
            import seed_data
            seed_data.seed()
            print("Auto-seeded database for initial deployment.")
    except Exception as e:
        print("Database auto-init notice:", e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
