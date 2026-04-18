# Music Converter

Convert sheet music PDFs into machine-readable notation formats using Audiveris optical music recognition.

## The Story

From time to time, I find myself needing to convert sheet music into guitar / bass tabs. There is an online service that does this, but it's notoriously unreliable. After several failed attempts to find a working service (and even trying to pay for one), I decided to build my own solution.

The result: a straightforward Docker-based workflow that converts sheet music PDFs into files compatible with [MuseScore](https://musescore.org/en/download) and other music notation software. Success rate has been pretty high so far, with minimal editing required depending on source PDF quality.

## How It Works

This project wraps [**Audiveris**](https://github.com/Audiveris/audiveris), an open-source Optical Music Recognition (OMR) engine, in a Docker container for easy batch processing.

## Requirements

- **Docker**: 20.10+ (with Compose V2)
- **Disk space**: ~2GB for image, ~500MB-1GB per processed file
- **Memory**: 4GB minimum (configurable in docker-compose.yml)
- **OS**: Linux, macOS, or Windows with Docker Desktop
- **CPU**: Any modern processor (amd64 architecture)

## Supported Formats

**Input**: PDF, PNG, JPG, and other common image formats  
**Output**: MXL (MuseScore), XML, PDF (with recognized notation overlaid)

## Quick Start

### Initial Setup
```bash
docker compose build  # Takes several minutes, builds ~1.5GB image
```

### Process Your Music
```bash
# 1. Copy your sheet music PDF/image to the input/ directory
cp your-sheet-music.pdf input/

# 2. Run the processor
docker compose up

# 3. Wait for completion (watch the logs)

# 4. Open the output file in MuseScore
open output/your-sheet-music.mxl  # macOS
# or
xdg-open output/your-sheet-music.mxl  # Linux
```

## Custom Processing

For more control over Audiveris options:

```bash
docker compose run audiveris -batch -export -output /output /input/file.pdf
docker compose run audiveris -help  # View all Audiveris options
```

## Project Structure

```
.
├── input/              # Place your sheet music files here
├── output/             # Processed files appear here
├── Dockerfile          # Container definition
├── docker-compose.yml  # Docker Compose orchestration
└── entrypoint.sh       # Batch processing script
```

## Known Limitations

- **Quality dependent on source**: Blurry, low-contrast, or handwritten notation may produce poor results
- **Memory usage**: 4GB memory limit may not be enough for very large files; increase in docker-compose.yml if needed
- **Processing time**: Depends on file complexity; typically 30 seconds to 5 minutes per page
- **OCR accuracy**: Tesseract OCR may struggle with unusual fonts or languages

## Troubleshooting

**Error: "executable file not found in $PATH"**
- Rebuild the image without cache: `docker compose build --no-cache && docker compose up`
- Check build logs for dpkg errors during Audiveris installation

**Out of memory errors**
- Increase memory limit in docker-compose.yml: `memory: 8G`

**Poor recognition results**
- Ensure source PDF has good contrast and is not rotated
- Try pre-processing the image with a tool like ImageMagick to improve quality

## Credits

Built on [**Audiveris**](https://github.com/Audiveris/audiveris) — an excellent open-source Optical Music Recognition engine. This project is essentially a convenient Docker wrapper around Audiveris to automate batch processing.

## License

MIT License — See LICENSE file for details.

## Contributing

Found a bug or have an improvement? Issues and pull requests are welcome!
