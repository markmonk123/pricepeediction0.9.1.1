#!/bin/bash

# This script sets up the Cryptocurrency Price Prediction Dashboard project.

# Create necessary directories
mkdir -p pricepeediction0.9.1.1/public

# Copy SSL certificates
cp server-key.pem pricepeediction0.9.1.1/server-key.pem
cp server-cert.pem pricepeediction0.9.1.1/server-cert.pem

# Copy index.html
cp public/index.html pricepeediction0.9.1.1/public/index.html

# Copy priceprediction.py
cp priceprediction.py pricepeediction0.9.1.1/priceprediction.py

# Install npm dependencies
cd pricepeediction0.9.1.1
npm install

echo "Setup completed successfully."