mjavascript
const express = require('express');
const https = require('https');
const fs = require('fs');
const WebSocket = require('ws');
const cors = require('cors');
const { fetchMarketData } = require('./marketDataFetcher'); // Function to fetch market data

const app = express();
const PORT = 3000;

// Load SSL certificate
const server = https.createServer({
    key: fs.readFileSync('path/to/your/private-key.pem'),   // path to your SSL private key
    cert: fs.readFileSync('path/to/your/certificate.pem')    // path to your SSL certificate
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
        console.log(`Data from Python: ${data}`);
        // Here you could send the processed data to the front end via WebSocket
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

    // Handle messages from the client
    ws.on('message', (message) => {
        console.log(`Received from client: ${message}`);
        // Forward the message to the Python process
        pricePredictionProcess.stdin.write(message + '\n');
    });

    ws.on('close', () => {
        console.log('Client disconnected');
    });
});

// Initialize server and start the Python service
server.listen(PORT, () => {
    console.log(`Server is running on https://localhost:${PORT}`);
    startPricePredictionService();
});
