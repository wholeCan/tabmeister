# Tabmeister

Convert sheet music PDFs into machine-readable notation formats using Audiveris optical music recognition. Upload via a web interface and receive converted files by email.

## The Story

From time to time, I find myself needing to convert sheet music into guitar / bass tabs. There is an online service that does this, but it's notoriously unreliable. After several failed attempts to find a working service (and even trying to pay for one and have it flake out), I decided to build my own solution.

The result: a web-based system powered by [**Audiveris**](https://github.com/Audiveris/audiveris), an open-source Optical Music Recognition (OMR) engine. Upload your sheet music via the web form, and the converted MusicXML file is emailed to you when ready.

## How It Works

A three-service architecture:

1. **Web Form** (Flask) — Upload your PDF and email address
2. **Message Queue** (RabbitMQ) — Job coordination between web and worker
3. **Worker** (Audiveris Processor) — Converts PDFs to MusicXML notation

When you upload a PDF:
- Validated and queued for processing
- Worker processes the file with Audiveris
- Converted MusicXML (.mxl) file is emailed to you
- System logs all successes, failures, and invalid attempts

## Requirements

- **Docker**: 20.10+ (with Compose V2)
- **Memory**: 4GB allocated to Docker
- **OS**: Linux, macOS, or Windows with Docker Desktop
- **SMTP Access**: Gmail account with app password, or any SMTP server

## Quick Start

### 1. Configure Environment

```bash
cp env.example .env
```

Edit `.env` with your SMTP credentials (Gmail example):
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=your_16_char_app_password
SMTP_FROM=your_gmail@gmail.com
OWNER_EMAIL=your_owner_email@gmail.com
FLASK_SECRET_KEY=generate_a_random_string
```

**Note**: For Gmail, generate an [App Password](https://myaccount.google.com/apppasswords) (requires 2FA).

### 2. Start Services

```bash
docker compose up --build
```

Services launch:
- **Web Form**: http://localhost:5000
- **RabbitMQ UI**: http://localhost:15672 (guest/guest)
- **Worker**: Processes jobs in background

### 3. Upload and Convert

Open http://localhost:5000, upload a PDF (max 300KB), enter your email, and wait for the converted file via email.

## Supported Formats

**Input**: PDF files (max 300KB)  
**Output**: MusicXML (.mxl) — open in MuseScore, Finale, Sibelius, or other notation software

## Project Structure

```
.
├── web/                # Flask web form and upload handler
├── worker/             # Audiveris processor and email sender
├── uploads/            # Temporary PDF storage
├── output/             # Converted MusicXML files
├── logs/               # Processing logs (JSON)
├── docker-compose.yml  # Multi-service orchestration
└── env.example         # Environment variable template
```

## Monitoring

### Check Conversion Logs
```bash
tail -f logs/conversions.log
```

### View RabbitMQ Queue Status
Open http://localhost:15672 to see pending and processed jobs.

### Check Invalid Upload Attempts
```bash
tail -f logs/invalid_uploads.log
```

## Known Limitations

- **Quality dependent on source**: Blurry or low-contrast PDFs may produce poor results
- **File size limit**: 300KB (adjust in web/app.py if needed)
- **Processing time**: Typically 30 seconds to 5 minutes per file
- **Timeout**: Jobs taking >5 minutes are marked as failed

## Troubleshooting

**Email not sending**
- Verify `.env` credentials and SMTP settings
- For Gmail: confirm app password was generated (not account password)
- Check logs: `docker logs tabmeister-worker | grep -i email`

**RabbitMQ queue not responding**
- Wait 15 seconds for RabbitMQ to start after `docker compose up`
- Check health: `docker logs tabmeister-rabbitmq | grep ready`

**PDF upload rejected**
- File must be a valid PDF (not renamed); verify with `file your_file.pdf`
- Check file size (max 300KB)
- Ensure email is valid format

**Poor recognition results**
- Try a different PDF with higher contrast
- Ensure the PDF is not rotated or heavily compressed

## More Details

For detailed configuration, troubleshooting, and production deployment guidance, see [SETUP.md](SETUP.md).

## Credits

Built on [**Audiveris**](https://github.com/Audiveris/audiveris) — an excellent open-source Optical Music Recognition engine. This project is essentially a convenient Docker wrapper around Audiveris to automate batch processing.

## License

MIT License — See LICENSE file for details.

## Contributing

Found a bug or have an improvement? Issues and pull requests are welcome!
