#!/bin/sh
set -e

files=$(find /input -maxdepth 1 -type f \( -iname "*.pdf" -o -iname "*.png" -o -iname "*.jpg" -o -iname "*.tiff" \) | tr '\n' ' ')

if [ -z "$files" ]; then
  echo "No input files found in /input"
  exit 1
fi

exec /opt/audiveris/bin/Audiveris -batch -export -output /output $files
