from flask import Blueprint, jsonify

jobs_bp = Blueprint("jobs", __name__)

# Dummy job data
dummy_jobs = [
    {"job_id": 100, "title": "Python Developer", "company": "Netfotech", "description": "Develop Python applications", "duration": 90}
]

@jobs_bp.route("/jobs", methods=["GET"])
def get_jobs():
    return jsonify({"jobs": dummy_jobs}), 200

@jobs_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_by_id(job_id):
    job = next((j for j in dummy_jobs if j["job_id"] == job_id), None)
    if job:
        return jsonify({"job": job}), 200
    return jsonify({"error": f"Job with ID {job_id} not found"}), 404
