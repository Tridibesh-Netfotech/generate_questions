from flask import Blueprint, jsonify

jobs_bp = Blueprint("jobs", __name__)

# dummy job data
dummy_jobs = [
    {"job_id": 1, "title": "Python Developer", "company": "Netfotech"},
    {"job_id": 2, "title": "Frontend Engineer", "company": "Google"},
    {"job_id": 3, "title": "Data Analyst", "company": "Tcs"}
]

@jobs_bp.route("/jobs", methods=["GET"])
def get_jobs():
    return jsonify({"jobs": dummy_jobs})

@jobs_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_by_id(job_id):
    job = next((j for j in dummy_jobs if j["job_id"] == job_id), None)
    if job:
        return jsonify(job)
    return jsonify({"error": "Job not found"}), 404
