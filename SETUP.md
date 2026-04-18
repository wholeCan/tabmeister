# Tabmeister Web + Queue Setup

This is the complete setup guide for the web-based sheet music conversion system.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- A Gmail account with 2FA enabled for email credentials (or any SMTP server)

## Quick Start

### 1. Configure Environment Variables

Copy the example env file and fill in your SMTP credentials:

```bash
cp env.example .env
```

Edit `.env` with your actual credentials:

```bash
# For Gmail:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=your_16_char_app_password  # Generate at https://myaccount.google.com/apppasswords
SMTP_FROM=your_gmail@gmail.com
OWNER_EMAIL=your_owner_email@gmail.com
FLASK_SECRET_KEY=<generate a random string>
```

**Important**: For Gmail, you must use an **App Password**, not your account password. Enable 2FA on your Google account, then generate an App Password at https://myaccount.google.com/apppasswords.

### 2. Build and Start Services

```bash
docker-compose up --build
```

This will:
- Build the web Flask app (port 5000)
- Start RabbitMQ (port 15672, management UI)
- Start the Audiveris worker (processes jobs)

### 3. Access the Web Form

Open your browser to:
```
http://localhost:5000
```

Upload a PDF file (max 300KB) and enter your email address. You'll receive a confirmation, and the converted MusicXML file will be emailed to you when processing completes.

## System Architecture

```
Web Form (Flask)
    ↓ (POST /upload with PDF + email)
    ↓
RabbitMQ Queue (omr_jobs)
    ↓ (JSON message with file path)
    ↓
Worker (Audiveris Processor)
    ↓ (runs /opt/audiveris/bin/Audiveris)
    ↓
Email Results
    ↓ (sends .mxl file to user + notifies owner)
Logging
    ↓ (JSON logs in ./logs/)
```

## Key Directories

- `./uploads/` - Temporary storage of uploaded PDFs (cleaned up after processing)
- `./output/` - Audiveris output (MusicXML .mxl files)
- `./logs/` - Processing logs:
  - `conversions.log` - One JSON line per job (success/fail, timing, etc.)
  - `invalid_uploads.log` - Invalid upload attempts (non-PDF, oversized, etc.)

## Monitoring

### RabbitMQ Management UI
Access at http://localhost:15672 (guest/guest)
- Verify the `omr_jobs` queue exists
- Watch job messages arrive and get processed

### Check Logs

View conversion results:
```bash
tail -f ./logs/conversions.log
```

View invalid upload attempts:
```bash
tail -f ./logs/invalid_uploads.log
```

## Validation Rules

The web form enforces:
1. **Email**: Must be a valid email format
2. **File**: Must be a `.pdf` file with `application/pdf` MIME type
3. **Size**: Max 300KB (307,200 bytes)

Invalid attempts are logged with timestamp, IP, email attempted, and reason.

## Email Flow

### Successful Conversion
User receives:
- Subject: "Sheet Music Conversion Complete - {filename}"
- Body: Confirmation message + instructions
- Attachment: `.mxl` MusicXML file (ready for MuseScore/Finale/Sibelius)

Owner receives:
- Subject: "[Tabmeister] Conversion Success - {filename}"
- Body: Job ID, user email, filename, processing duration

### Failed Conversion
User receives:
- Subject: "Sheet Music Conversion Failed - {filename}"
- Body: Apology message with error details

Owner receives:
- Subject: "[Tabmeister] Conversion Failed - {filename}"
- Body: Job details and error message for debugging

### Timeout (5+ minutes)
Same as failure, with specific timeout message.

## Error Handling

The system gracefully handles:
- **Audiveris failure**: Logged, user notified by email, worker continues
- **Timeout**: If a file takes >5 minutes, job is marked failed, user notified
- **SMTP failure**: Error logged, processing continues, doesn't block other jobs
- **RabbitMQ disconnect**: Worker automatically retries with exponential backoff (max 30s delay)

## Troubleshooting

### "Connection refused" when building
- Docker may not be running. Start Docker Desktop or docker daemon.

### RabbitMQ queue not appearing in management UI
- Wait 10-15 seconds after `docker-compose up` for RabbitMQ to fully start
- Verify healthcheck: `docker logs tabmeister-rabbitmq | grep -i "ready to accept"`

### Email not sending
- Check `.env` credentials are correct
- Verify SMTP port (Gmail uses 587 for TLS)
- For Gmail, ensure you generated an App Password, not using account password
- Check worker logs: `docker logs tabmeister-worker | grep -i "email"`

### PDF upload fails with "invalid MIME type"
- Ensure file is actually a PDF (not renamed from another format)
- Try: `file your_file.pdf` (should say "PDF" not "data")

### Audiveris timeout or crash
- Check if PDF is corrupted: try a different sheet music file
- Check worker memory: Docker may need more than 4GB allocated
- Check worker logs: `docker logs tabmeister-worker`

## Stopping Services

```bash
docker-compose down
```

This preserves logs and uploaded files (in bind-mounted volumes). Logs and output files persist on the host.

To clean up everything including logs:
```bash
docker-compose down -v
```

## Production Deployment Notes

For production:
1. Use proper secrets management (not .env file)
2. Use a persistent message broker (RabbitMQ cluster, or managed service)
3. Add database logging instead of JSON files
4. Set up monitoring/alerting on queue depth and failure rates
5. Implement authentication on the web form
6. Use HTTPS/TLS for the web interface
7. Scale worker replicas based on queue depth: `docker-compose up --scale worker=3`

## Development/Testing

### Test with a local PDF
```bash
# Download a test sheet music PDF or create one
# Then upload via the web form at http://localhost:5000
```

### Verify queue processing
```bash
# Check RabbitMQ management UI
# Message should be consumed quickly (30 sec - 5 min depending on file)
```

### Check file permissions
```bash
# Ensure ./uploads, ./output, ./logs directories are writable
ls -la ./uploads/ ./output/ ./logs/
```

## Architecture Decision Notes

### Why separate web and worker containers?
Decoupling allows:
- Web form stays responsive (no blocking conversion)
- Worker can be scaled independently
- Either can restart without affecting the other

### Why RabbitMQ for the queue?
Standard, reliable message broker:
- Persistent (survives restarts)
- Acknowledges (prevents job loss)
- Management UI for debugging
- Easily scales to multiple workers

### Why bind-mounted volumes (not named volumes)?
Easier to inspect and debug:
- Direct access to logs and output on host: `./logs/`, `./output/`
- Can delete individual files without container interaction
- No Docker volume plugin dependency
