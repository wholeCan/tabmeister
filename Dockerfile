FROM --platform=linux/amd64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    xdg-utils \
    openjdk-17-jre \
    tesseract-ocr \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data

# 2. Download and install Audiveris .deb
# Stub xdg-desktop-menu so the post-install script doesn't fail in a headless container
RUN printf '#!/bin/sh\nexit 0\n' > /usr/local/bin/xdg-desktop-menu && \
    chmod +x /usr/local/bin/xdg-desktop-menu

RUN wget -q -O audiveris.deb "https://github.com/Audiveris/audiveris/releases/download/5.10.2/Audiveris-5.10.2-ubuntu24.04-x86_64.deb" && \
    dpkg -i audiveris.deb; apt-get install -f -y && \
    dpkg -i audiveris.deb && \
    rm audiveris.deb

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
