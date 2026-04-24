import os
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps

import pika
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-change-me")

UPLOADS_DIR = Path("/uploads")
LOGS_DIR = Path("/logs")
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB

# Ensure directories exist
UPLOADS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# RabbitMQ config
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

QUEUE_NAME = "omr_jobs"


def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        connection_attempts=5,
        retry_delay=2,
    )
    return pika.BlockingConnection(parameters)


def publish_job(job_id, email, filename, upload_path):
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        message = {
            "job_id": job_id,
            "email": email,
            "filename": filename,
            "upload_path": upload_path,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
        return True
    except Exception as e:
        app.logger.error(f"Failed to publish job: {e}")
        return False


def log_invalid_upload(ip, email_attempted, reason):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "email_attempted": email_attempted,
        "reason": reason,
    }
    try:
        with open(LOGS_DIR / "invalid_uploads.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        app.logger.error(f"Failed to log invalid upload: {e}")


def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


@app.route("/", methods=["GET"])
def index():
    venmo_link = os.getenv("VENMO_LINK", "")
    return render_template("index.html", venmo_link=venmo_link)


@app.route("/upload", methods=["POST"])
def upload():
    client_ip = request.remote_addr
    email = request.form.get("email", "").strip()
    file = request.files.get("file")

    # Validate email
    if not email:
        log_invalid_upload(client_ip, "", "email_missing")
        return (
            jsonify({"error": "Email address is required."}),
            400,
        )

    if not validate_email(email):
        log_invalid_upload(client_ip, email, "invalid_email_format")
        return (
            jsonify({"error": "Invalid email address format."}),
            400,
        )

    # Validate file
    if not file or file.filename == "":
        log_invalid_upload(client_ip, email, "file_missing")
        return (
            jsonify({"error": "PDF file is required."}),
            400,
        )

    # Validate file extension and MIME type
    if not file.filename.lower().endswith(".pdf"):
        log_invalid_upload(client_ip, email, "invalid_file_extension")
        return (
            jsonify({"error": "Only PDF files are supported."}),
            400,
        )

    if file.mimetype != "application/pdf":
        log_invalid_upload(client_ip, email, "invalid_mimetype")
        return (
            jsonify({"error": "File must be a valid PDF."}),
            400,
        )

    # Read and validate file size
    file_data = file.read()
    if len(file_data) == 0:
        log_invalid_upload(client_ip, email, "empty_file")
        return (
            jsonify({"error": "File is empty."}),
            400,
        )

    if len(file_data) > MAX_FILE_SIZE:
        log_invalid_upload(client_ip, email, "file_too_large")
        return (
            jsonify(
                {
                    "error": f"File exceeds maximum size of {MAX_FILE_SIZE // 1024}KB."
                }
            ),
            400,
        )

    # Save file with UUID prefix
    job_id = str(uuid.uuid4())
    original_filename = file.filename
    saved_filename = f"{job_id}_{original_filename}"
    upload_path = UPLOADS_DIR / saved_filename

    try:
        with open(upload_path, "wb") as f:
            f.write(file_data)
    except Exception as e:
        app.logger.error(f"Failed to save file: {e}")
        return (
            jsonify({"error": "Failed to save file. Please try again."}),
            500,
        )

    # Publish to RabbitMQ
    if not publish_job(job_id, email, original_filename, f"/uploads/{saved_filename}"):
        return (
            jsonify(
                {
                    "error": "Failed to queue conversion job. Please try again."
                }
            ),
            500,
        )

    return jsonify(
        {
            "success": True,
            "message": f"File uploaded successfully! You will receive an email at {email} when your conversion is complete.",
            "job_id": job_id,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
