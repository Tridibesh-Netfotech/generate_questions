from flask import Blueprint, request, jsonify
from config import get_db_connection
from services.llm_client import evaluate_answer
import psycopg2

test_bp = Blueprint("test", __name__)


# ============================================================
# ✅ Start Test Endpoint
# ============================================================
@test_bp.route("/test/start/<question_set_id>", methods=["GET"])
def start_test(question_set_id):
    """
    Fetch all MCQ and Coding questions for a given question_set_id
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch questions (MCQ + Coding)
        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s
            AND type IN ('mcq', 'coding')
        """, (question_set_id,))
        questions = cursor.fetchall()

        # Convert to list of dicts
        columns = [desc[0] for desc in cursor.description]
        questions_list = [dict(zip(columns, row)) for row in questions]

        return jsonify({
            "question_set_id": question_set_id,
            "questions": questions_list
        }), 200

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# ✅ Submit Section API
# ============================================================
@test_bp.route("/test/submit_section", methods=["POST"])
def submit_section():
    """
    Receives section submission data and evaluates each response:
    {
        "question_set_id": "...",
        "section_name": "...",
        "candidate_id": null,
        "responses": [
            {
                "question_id": "...",
                "question_type": "mcq" or "coding",
                "question_text": "...",
                "correct_answer": "...",
                "candidate_answer": "..."
            }
        ]
    }
    """

    data = request.get_json()
    question_set_id = data.get("question_set_id")
    section_name = data.get("section_name")
    responses = data.get("responses", [])
    candidate_id = data.get("candidate_id")  # Can be null

    if not question_set_id or not responses:
        return jsonify({"error": "question_set_id and responses are required"}), 400

    conn = None
    cursor = None
    results_data = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for r in responses:
            question_id = r.get("question_id")
            qtype = r.get("question_type")
            question_text = r.get("question_text")
            correct_answer = r.get("correct_answer")
            candidate_answer = r.get("candidate_answer")

            if not all([question_id, qtype, question_text]):
                continue

            # ✅ Evaluate only MCQ & coding
            try:
                if qtype in ["mcq", "coding"]:
                    evaluation = evaluate_answer(
                        question_type=qtype,
                        question_text=question_text,
                        correct_answer=correct_answer,
                        candidate_answer=candidate_answer,
                    )
                else:
                    evaluation = {"score": None, "feedback": "Evaluation not applicable"}
            except Exception:
                evaluation = {"score": 0, "feedback": "Evaluation failed", "is_correct": False}

            # Extract score & feedback safely
            score = evaluation.get("score")
            feedback = evaluation.get("feedback", "")
            is_correct = evaluation.get("is_correct")

            results_data.append({
                "question_id": question_id,
                "question_set_id": question_set_id,
                "candidate_id": candidate_id,
                "candidate_answer": candidate_answer,
                "correct_answer": correct_answer,
                "score": score,
                "is_correct": is_correct,
                "feedback": feedback,
                "section_name": section_name
            })

            # ✅ Insert into results table with timestamp
            cursor.execute("""
                INSERT INTO results (
                    question_id, question_set_id, candidate_id,
                    candidate_answer, correct_answer,
                    score, is_correct, feedback, section_name, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                question_id,
                question_set_id,
                candidate_id,
                candidate_answer,
                correct_answer,
                score,
                is_correct,
                feedback,
                section_name
            ))

        conn.commit()
        return jsonify({
            "message": f"{len(results_data)} responses processed and stored.",
            "evaluations": results_data
        }), 201

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
