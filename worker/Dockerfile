FROM --platform=linux/amd64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    xdg-utils \
    openjdk-17-jre \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ita \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data

# 2. Download and install Audiveris .deb
# Stub xdg-desktop-menu so the post-install script doesn't fail in a headless container
# Download legacy-mode tessdata (Audiveris requires legacy engine, not LSTM-only)
RUN mkdir -p /root/.config/AudiverisLtd/audiveris/tessdata && \
    wget -q -O /root/.config/AudiverisLtd/audiveris/tessdata/eng.traineddata \
        "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" && \
    wget -q -O /root/.config/AudiverisLtd/audiveris/tessdata/ita.traineddata \
        "https://github.com/tesseract-ocr/tessdata/raw/main/ita.traineddata"

RUN printf '#!/bin/sh\nexit 0\n' > /usr/local/bin/xdg-desktop-menu && \
    chmod +x /usr/local/bin/xdg-desktop-menu

RUN wget -q -O audiveris.deb "https://github.com/Audiveris/audiveris/releases/download/5.10.2/Audiveris-5.10.2-ubuntu24.04-x86_64.deb" && \
    dpkg -i audiveris.deb; apt-get install -f -y && \
    dpkg -i audiveris.deb && \
    rm audiveris.deb && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Python dependencies
WORKDIR /worker
COPY worker/requirements.txt .
RUN python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

# 4. Copy worker script
COPY worker/worker.py .

CMD ["python3", "worker.py"]
