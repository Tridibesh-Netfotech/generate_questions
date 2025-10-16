
from flask import Blueprint, request, jsonify
from services.generator import generate_questions
import traceback
from config import get_db_connection
from utils.ids import gen_uuid
import datetime
import json
import requests

questions_bp = Blueprint("questions", __name__)

@questions_bp.route("/generate-test", methods=["POST"])
def generate_test():
    data = request.get_json()
    if not data or "skills" not in data:
        return jsonify({"error": "Invalid request, missing skills"}), 400
    try:
        questions = generate_questions(data)
        return jsonify({"status": "success", "questions": questions}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@questions_bp.route("/finalize-test", methods=["POST"])
def finalize_test():
    data = request.get_json()
    if not data or "questions" not in data:
        return jsonify({"error": "Invalid request, missing questions"}), 400

    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400

    # fetch job details from job api
    try:
        job_response = requests.get(f"http://127.0.0.1:5000/api/v1/jobs/{job_id}")
        if job_response.status_code != 200:
            return jsonify({"error": f"Job with ID {job_id} not found"}), 404
        job_data = job_response.json().get("job", {})
    except Exception as e:
        print("Error fetching job data:", e)
        return jsonify({"error": "Failed to fetch job data"}), 500

    test_title = job_data.get("title", "Untitled Test")
    test_description = job_data.get("description", "")
    total_duration = job_data.get("duration", 60)
    created_at = datetime.datetime.utcnow()
    expiry_time = created_at + datetime.timedelta(hours=48)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        question_set_id = gen_uuid()

        # Insert into question_set table
        cur.execute("""
            INSERT INTO question_set (id, job_id, title, description, duration, created_at, expiry_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            question_set_id,
            job_id,
            test_title,
            test_description,
            total_duration,
            created_at,
            expiry_time
        ))

        # Insert all questions
        for q in data["questions"]:
            question_id = q.get("question_id", gen_uuid())
            cur.execute("""
                INSERT INTO questions (
                    id, question_set_id, type, skill, difficulty,
                    content, time_limit, positive_marking, negative_marking, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                question_id,
                question_set_id,
                q["type"],
                q["skill"],
                q["difficulty"],
                json.dumps(q["content"]),
                q.get("time_limit", 60),
                q.get("positive_marking", 0),
                q.get("negative_marking", 0),
                created_at
            ))

        conn.commit()
        cur.close()

        return jsonify({
            "status": "success",
            "question_set_id": question_set_id,
            "job_id": job_id,
            "job_title": test_title,
            "expiry_time": expiry_time.isoformat(),
            "message": f"Test '{test_title}' stored successfully"
        }), 201

    except Exception as e:
        print("Database error:", e)
        traceback.print_exc()
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()
