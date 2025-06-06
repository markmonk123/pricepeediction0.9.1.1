#!/bin/bash

# Create necessary directories
mkdir -p public

# Copy SSL certificates
cp server-key.pem public/
cp server-cert.pem public/

# Copy index.html
cp public/index.html public/

# Copy priceprediction.py
cp priceprediction.py .

# Install npm dependencies
npm install

echo "Setup completed successfully."