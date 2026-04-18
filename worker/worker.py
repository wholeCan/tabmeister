import os
import json
import time
import logging
import smtplib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

import pika

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "")

UPLOADS_DIR = Path("/uploads")
OUTPUT_DIR = Path("/output")
LOGS_DIR = Path("/logs")

QUEUE_NAME = "omr_jobs"
AUDIVERIS_TIMEOUT = 300  # 5 minutes


def send_email(to_addr, subject, body_text, attachments=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        for attachment_path in attachments or []:
            try:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {Path(attachment_path).name}",
                )
                msg.attach(part)
            except Exception as e:
                logger.error(f"Failed to attach file {attachment_path}: {e}")

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_addr, msg.as_string())
        logger.info(f"Email sent to {to_addr}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_addr}: {e}")
        return False


def log_conversion(job_id, email, filename, status, duration_sec, error_msg=None):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "email": email,
        "filename": filename,
        "status": status,
        "duration_sec": round(duration_sec, 1),
    }
    if error_msg:
        log_entry["error"] = error_msg
    try:
        with open(LOGS_DIR / "conversions.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log conversion: {e}")


def find_and_rename_output(original_filename, files_before):
    """Find new files created by Audiveris and rename to {original_filename}_converted.mxl"""
    stem = Path(original_filename).stem
    files_after = set(OUTPUT_DIR.glob("*.mxl"))
    new_files = files_after - files_before

    renamed_files = []
    for new_file in sorted(new_files):
        new_name = OUTPUT_DIR / f"{stem}_converted.mxl"
        try:
            new_file.rename(new_name)
            renamed_files.append(str(new_name))
            logger.info(f"Renamed {new_file.name} to {new_name.name}")
        except Exception as e:
            logger.error(f"Failed to rename output file: {e}")
            renamed_files.append(str(new_file))

    return renamed_files


def process_job(ch, method, properties, body):
    start_time = time.time()
    msg = json.loads(body)
    job_id = msg["job_id"]
    email = msg["email"]
    filename = msg["filename"]
    upload_path = msg["upload_path"]

    logger.info(f"Processing job {job_id} for {email}: {filename}")

    try:
        # Capture current files before running Audiveris
        files_before = set(OUTPUT_DIR.glob("*.mxl"))

        # Run Audiveris
        result = subprocess.run(
            [
                "/opt/audiveris/bin/Audiveris",
                "-batch",
                "-export",
                "-output",
                str(OUTPUT_DIR),
                upload_path,
            ],
            capture_output=True,
            text=True,
            timeout=AUDIVERIS_TIMEOUT,
        )

        if result.returncode != 0:
            error_msg = result.stderr or "Audiveris failed with no error message"
            logger.error(f"Audiveris failed for {job_id}: {error_msg}")
            duration = time.time() - start_time
            log_conversion(
                job_id, email, filename, "fail", duration, error_msg
            )
            send_email(
                email,
                f"Sheet Music Conversion Failed - {filename}",
                f"Sorry, processing for your file '{filename}' has failed and the administrator has been contacted.\n\n"
                f"Please try again with a different file.",
            )
            send_email(
                OWNER_EMAIL,
                f"[Tabmeister] Conversion Failed - {filename}",
                f"Job {job_id}\nEmail: {email}\nFilename: {filename}\n"
                f"Error: {error_msg[:200]}",
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Find and rename output files
        output_files = find_and_rename_output(filename, files_before)
        duration = time.time() - start_time

        if not output_files:
            logger.warning(f"No output files found for job {job_id}")
            log_conversion(job_id, email, filename, "partial", duration)
            send_email(
                email,
                f"Sheet Music Conversion Complete - {filename}",
                f"Your sheet music file '{filename}' has been processed.\n\n"
                f"Processing completed but no output files were generated. "
                f"This may happen with certain types of sheet music.",
            )
        else:
            log_conversion(job_id, email, filename, "success", duration)
            send_email(
                email,
                f"Sheet Music Conversion Complete - {filename}",
                f"Your sheet music file '{filename}' has been successfully converted!\n\n"
                f"The MusicXML file is attached. You can now open it in MuseScore, "
                f"Finale, Sibelius, or other notation software.",
                attachments=output_files,
            )

        send_email(
            OWNER_EMAIL,
            f"[Tabmeister] Conversion Success - {filename}",
            f"Job {job_id}\nEmail: {email}\nFilename: {filename}\n"
            f"Duration: {duration:.1f}s",
        )

        logger.info(f"Job {job_id} completed successfully in {duration:.1f}s")

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        error_msg = "Conversion timed out after 5 minutes"
        logger.error(f"Job {job_id} timed out")
        log_conversion(job_id, email, filename, "fail", duration, error_msg)
        send_email(
            email,
            f"Sheet Music Conversion Failed - {filename}",
            f"Sorry, processing for your file '{filename}' has failed and the administrator has been contacted.\n\n"
            f"Please try again with a different file.",
        )
        send_email(
            OWNER_EMAIL,
            f"[Tabmeister] Conversion Timeout - {filename}",
            f"Job {job_id}\nEmail: {email}\nFilename: {filename}",
        )

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        logger.error(f"Job {job_id} failed with exception: {e}")
        log_conversion(job_id, email, filename, "fail", duration, error_msg)
        send_email(
            email,
            f"Sheet Music Conversion Failed - {filename}",
            f"Sorry, processing for your file '{filename}' has failed and the administrator has been contacted.\n\n"
            f"Please try again with a different file.",
        )
        send_email(
            OWNER_EMAIL,
            f"[Tabmeister] Conversion Error - {filename}",
            f"Job {job_id}\nEmail: {email}\nFilename: {filename}\n"
            f"Error: {error_msg}",
        )

    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def connect_with_retry(max_retries=10, retry_delay=5):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )

    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(parameters)
            logger.info("Connected to RabbitMQ")
            return connection
        except pika.exceptions.AMQPConnectionError:
            if attempt < max_retries - 1:
                wait_time = min(retry_delay * (2 ** attempt), 30)
                logger.warning(
                    f"RabbitMQ connection failed. Retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logger.error("Failed to connect to RabbitMQ after all retries")
                raise


def main():
    logger.info("Tabmeister worker starting")

    # Ensure directories exist
    UPLOADS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    connection = connect_with_retry()
    channel = connection.channel()

    # Declare queue
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=process_job,
    )

    logger.info(f"Listening on queue '{QUEUE_NAME}'...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        channel.stop_consuming()
        connection.close()


if __name__ == "__main__":
    main()
