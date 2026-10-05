import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ssc_cgl.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        full_name TEXT NOT NULL,
        target_year INTEGER DEFAULT 2025,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Subjects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT UNIQUE NOT NULL,
        description TEXT
    )
    """)

    # Papers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        exam_name TEXT DEFAULT 'SSC CGL',
        year INTEGER NOT NULL,
        tier TEXT DEFAULT 'Tier 1',
        shift TEXT NOT NULL,
        duration_minutes INTEGER DEFAULT 60,
        marks_per_question REAL DEFAULT 2.0,
        negative_marks REAL DEFAULT 0.50,
        instructions TEXT,
        paper_type TEXT DEFAULT 'official_pyq', -- 'official_pyq', 'model_paper', 'practice_paper'
        source_attribution TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        subject_id INTEGER REFERENCES subjects(id),
        topic TEXT,
        difficulty TEXT DEFAULT 'Medium',
        question_text TEXT NOT NULL,
        question_image TEXT,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL, -- 'A', 'B', 'C', 'D'
        explanation TEXT,
        question_type TEXT DEFAULT 'official_pyq', -- 'official_pyq', 'model_question', 'practice_question'
        order_num INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Test attempts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT DEFAULT 'in_progress', -- 'in_progress', 'completed', 'abandoned'
        total_questions INTEGER DEFAULT 0,
        attempted_questions INTEGER DEFAULT 0,
        correct_answers INTEGER DEFAULT 0,
        wrong_answers INTEGER DEFAULT 0,
        unanswered_questions INTEGER DEFAULT 0,
        positive_marks REAL DEFAULT 0.0,
        negative_marks REAL DEFAULT 0.0,
        final_score REAL DEFAULT 0.0,
        max_marks REAL DEFAULT 0.0,
        percentage REAL DEFAULT 0.0,
        accuracy REAL DEFAULT 0.0,
        time_taken_seconds INTEGER DEFAULT 0,
        current_question_index INTEGER DEFAULT 0
    )
    """)

    # User answers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL REFERENCES test_attempts(id) ON DELETE CASCADE,
        question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
        selected_option TEXT, -- 'A', 'B', 'C', 'D' or NULL
        is_correct INTEGER, -- 1 for correct, 0 for incorrect, NULL for unattempted
        is_marked_for_review INTEGER DEFAULT 0,
        is_submitted INTEGER DEFAULT 0,
        time_spent_seconds INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(attempt_id, question_id)
    )
    """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
