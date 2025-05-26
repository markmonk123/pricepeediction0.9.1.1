const express = require('express');
const https = require('https');
const fs = require('fs');
const WebSocket = require('ws');
const cors = require('cors');
const { fetchMarketData } = require('./marketDataFetcher'); // Function to fetch market data
const { spawn } = require('child_process'); // Add this line

const app = express();
const PORT = 3000;

// Load SSL certificate
const server = https.createServer({
    key: fs.readFileSync('server-key.pem'),
    cert: fs.readFileSync('server-cert.pem')
}, app);

// Enable CORS
app.use(cors());

// Initialize WebSocket server
const wss = new WebSocket.Server({ server });

let pricePredictionProcess;

// Start Python PricePrediction Service
const startPricePredictionService = () => {
    pricePredictionProcess = spawn('python', ['priceprediction0.9.1.1.py']);

    pricePredictionProcess.stdout.on('data', (data) => {
        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(data.toString());
            }
        });
    });

    pricePredictionProcess.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });

    pricePredictionProcess.on('close', (code) => {
        console.log(`PricePrediction process exited with code ${code}`);
    });
};

// Set up WebSocket connection
wss.on('connection', (ws) => {
    console.log('Client connected');
    // Handle incoming messages from clients
    ws.on('message', (message) => {
        console.log(`Received from client: ${message}`);
        pricePredictionProcess.stdin.write(message + '\n');
    });
    ws.on('close', () => {
        console.log('Client disconnected');
    });
    ws.on('error', (err) => {
        console.error('WebSocket error:', err);
    });
});

wss.on('error', (err) => {
    console.error('WebSocket Server error:', err);
});

// Initialize server and start the Python service
server.listen(PORT, () => {
    console.log(`Server is running on https://localhost:${PORT}`);
    startPricePredictionService();
});

