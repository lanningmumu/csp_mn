# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'exam.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            student_name TEXT NOT NULL DEFAULT '',
            total INTEGER NOT NULL,
            correct INTEGER NOT NULL,
            accuracy REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exam_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL REFERENCES exams(id),
            question_id INTEGER NOT NULL,
            user_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL
        );
    ''')
    # Add student_name column if migrating from old schema
    try:
        conn.execute('SELECT student_name FROM exams LIMIT 1')
    except sqlite3.OperationalError:
        conn.execute('ALTER TABLE exams ADD COLUMN student_name TEXT NOT NULL DEFAULT ""')
    conn.commit()
    conn.close()


def save_exam(student_name, total, correct, accuracy, answers):
    """answers: list of (question_id, user_answer, is_correct)"""
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO exams (student_name, total, correct, accuracy) VALUES (?, ?, ?, ?)',
        (student_name, total, correct, accuracy)
    )
    exam_id = cur.lastrowid
    for qid, ua, ok in answers:
        conn.execute(
            'INSERT INTO exam_answers (exam_id, question_id, user_answer, is_correct) VALUES (?, ?, ?, ?)',
            (exam_id, qid, ua, 1 if ok else 0)
        )
    conn.commit()
    conn.close()
    return exam_id


def get_exam_list(limit=50, student_name=None):
    conn = get_db()
    if student_name:
        rows = conn.execute(
            'SELECT id, created_at, student_name, total, correct, accuracy FROM exams WHERE student_name = ? ORDER BY id DESC LIMIT ?',
            (student_name, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT id, created_at, student_name, total, correct, accuracy FROM exams ORDER BY id DESC LIMIT ?',
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_students():
    conn = get_db()
    rows = conn.execute(
        'SELECT DISTINCT student_name FROM exams WHERE student_name != "" ORDER BY student_name'
    ).fetchall()
    conn.close()
    return [r['student_name'] for r in rows]


def get_exam_detail(exam_id):
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    if not exam:
        conn.close()
        return None
    answers = conn.execute(
        'SELECT * FROM exam_answers WHERE exam_id = ?', (exam_id,)
    ).fetchall()
    conn.close()
    return {
        'exam': dict(exam),
        'answers': [dict(a) for a in answers]
    }


def get_wrong_question_ids(student_name=None):
    """Return question IDs that the user has ever gotten wrong, optionally filtered by student."""
    conn = get_db()
    if student_name:
        rows = conn.execute('''
            SELECT DISTINCT ea.question_id
            FROM exam_answers ea
            JOIN exams e ON e.id = ea.exam_id
            WHERE ea.is_correct = 0 AND e.student_name = ?
        ''', (student_name,)).fetchall()
    else:
        rows = conn.execute('''
            SELECT DISTINCT ea.question_id
            FROM exam_answers ea
            WHERE ea.is_correct = 0
        ''').fetchall()
    conn.close()
    return [r['question_id'] for r in rows]


def get_score_leaderboard(limit=20):
    """Top scores by single exam accuracy."""
    conn = get_db()
    rows = conn.execute('''
        SELECT student_name, MAX(accuracy) as best_accuracy, MAX(correct) as best_correct, MAX(total) as at_total
        FROM exams
        WHERE student_name != ''
        GROUP BY student_name
        ORDER BY best_accuracy DESC, best_correct DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_leaderboard(limit=20):
    """Top students by total correct answers across all exams."""
    conn = get_db()
    rows = conn.execute('''
        SELECT student_name, SUM(correct) as total_correct, COUNT(*) as exam_count,
               ROUND(CAST(SUM(correct) AS REAL) / SUM(total) * 100, 1) as overall_accuracy
        FROM exams
        WHERE student_name != ''
        GROUP BY student_name
        ORDER BY total_correct DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
