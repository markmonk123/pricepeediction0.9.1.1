import https from 'https';
import fs from 'fs';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import { WebSocketServer } from 'ws'; // Use ws for compatibility and features
import { fetchMarketData } from './marketDataFetcher.js';
import Coinbase from 'coinbase';
import { CoinbaseAdvancedTrade } from 'coinbase-advanced-node';

// Parse CLI arguments with yargs
const argv = yargs(hideBin(process.argv))
    .option('port', {
        alias: 'p',
        type: 'number',
        description: 'Port to run the server on',
        default: process.env.PORT ? parseInt(process.env.PORT) : 9000
    })
    .argv;

const PORT = argv.port;

// Load SSL certificate
u// Assuming certs are in /etc/ssl/certs and /etc/ssl/private (common on Linux)
const SSL_KEY_PATH = process.env.SSL_KEY_PATH || '/etc/ssl/private/ssl-cert-snakeoil.key';
const SSL_CERT_PATH = process.env.SSL_CERT_PATH || '/etc/ssl/certs/ssl-cert-snakeoil.pem';

let server;
try {
    server = https.createServer({
        key: fs.readFileSync(SSL_KEY_PATH),
        cert: fs.readFileSync(SSL_CERT_PATH)
    });
    console.log('SSL certificates loaded successfully.');
} catch (err) {
    console.error('Error loading SSL certificates:', err);
    process.exit(1); // Exit if SSL setup fails
}

// Initialize WebSocket server (secure)
const wss = new WebSocketServer({ server });

console.log('WebSocket server initialized.');

// --- Technical Analysis Functions (SMA, Bollinger Bands, MACD, DMI/ADX) ---

function sma(arr, window) {
    if (!Array.isArray(arr) || arr.length === 0 || !Number.isInteger(window) || window <= 0) {
        console.error('Invalid input to SMA function.');
        return new Array(arr.length).fill(null); // Return null array
    }
    let result = [];
    for (let i = 0; i < arr.length; i++) {
        if (i < window - 1) {
            result.push(null);
        } else {
            const slice = arr.slice(i - window + 1, i + 1);
            const sum = slice.reduce((a, b) => a + b, 0);
            result.push(sum / window);
        }
    }
    return result;
}

function bollingerBands(arr, window = 20, numStdDev = 2) {
    if (!Array.isArray(arr) || arr.length === 0 || !Number.isInteger(window) || window <= 0) {
        console.error('Invalid input to bollingerBands function.');
        return { middle: [], upper: [], lower: [] };
    }
    let middle = sma(arr, window);
    let upper = [];
    let lower = [];
    for (let i = 0; i < arr.length; i++) {
        if (i < window - 1) {
            upper.push(null);
            lower.push(null);
        } else {
            const slice = arr.slice(i - window + 1, i + 1);
            const mean = middle[i];
            const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / window;
            const stdDev = Math.sqrt(variance);
            upper.push(mean + numStdDev * stdDev);
            lower.push(mean - numStdDev * stdDev);
        }
    }
    return { middle, upper, lower };
}

function macd(prices, shortWindow = 12, longWindow = 26) {
    if (!Array.isArray(prices) || prices.length === 0) {
        console.error('Invalid input to MACD function.');
        return new Array(prices.length).fill(null);
    }
    const ema = (arr, window) => {
        if (!Array.isArray(arr) || arr.length === 0) return [];
        let k = 2 / (window + 1);
        let emaArr = [arr[0]];
        for (let i = 1; i < arr.length; i++) {
            emaArr.push(arr[i] * k + emaArr[i - 1] * (1 - k));
        }
        return emaArr;
    };
    const shortEma = ema(prices, shortWindow);
    const longEma = ema(prices, longWindow);
    return shortEma.map((val, i) => (val !== undefined && longEma[i] !== undefined) ? val - longEma[i] : null);
}

function dmi_adx(data, window = 14) {
    if (!Array.isArray(data) || data.length === 0) {
        console.error('Invalid input to dmi_adx function.');
        return { plusDI: [], minusDI: [], adx: [] };
    }
    let plusDI = [], minusDI = [], adx = [];
    let trArr = [], plusDMarr = [], minusDMarr = [];

    // Start loop from 1 to handle data[i-1] access
    for (let i = 1; i < data.length; i++) {
        if (!data[i] || !data[i - 1]) {
            console.warn(`Skipping index ${i} due to missing data.`);
            continue;
        }

        let upMove = data[i].high - data[i - 1].high;
        let downMove = data[i - 1].low - data[i].low;
        let plusDM = upMove > downMove && upMove > 0 ? upMove : 0;
        let minusDM = downMove > upMove && downMove > 0 ? downMove : 0;

        let tr = Math.max(
            data[i].high - data[i].low,
            Math.abs(data[i].high - data[i - 1].close),
            Math.abs(data[i].low - data[i - 1].close)
        );

        plusDMarr.push(plusDM);
        minusDMarr.push(minusDM);
        trArr.push(tr);
    }

    for (let i = window; i < trArr.length; i++) {
        let trSum = trArr.slice(i - window, i).reduce((a, b) => a + b, 0);
        let plusDMSum = plusDMarr.slice(i - window, i).reduce((a, b) => a + b, 0);
        let minusDMSum = minusDMarr.slice(i - window, i).reduce((a, b) => a + b, 0);

        if (trSum === 0) {
            console.warn(`Skipping ADX calculation at index ${i} due to zero TR sum.`);
            plusDI.push(null);
            minusDI.push(null);
            adx.push(null);
            continue;
        }

        let plus = 100 * (plusDMSum / trSum);
        let minus = 100 * (minusDMSum / trSum);
        let dx = 100 * Math.abs(plus - minus) / (plus + minus);
        plusDI.push(plus);
        minusDI.push(minus);
        adx.push(dx);
    }

    // Pad with nulls for alignment
    while (plusDI.length < data.length) plusDI.unshift(null);
    while (minusDI.length < data.length) minusDI.unshift(null);
    while (adx.length < data.length) adx.unshift(null);

    return { plusDI, minusDI, adx };
}

// --- Data Fetch & Analysis ---
async function fetchAndAnalyze() {
    try {
        // Use your fetchMarketData to get the latest candles (should return array of {timestamp, open, high, low, close, volume})
        const data = await fetchMarketData(1); // 1-minute candles, last 60 minutes

        if (!data || data.length === 0) {
            console.warn('No market data received.');
            return [];
        }

        const closes = data.map(d => d.close);
        const macdArr = macd(closes);
        const { plusDI, minusDI, adx } = dmi_adx(data);
        const sma20 = sma(closes, 20);
        const { middle: bbMiddle, upper: bbUpper, lower: bbLower } = bollingerBands(closes, 20, 2);

        return data.map((d, i) => ({
            ...d,
            macd: macdArr[i] ?? null,
            plusDI: plusDI[i] ?? null,
            minusDI: minusDI[i] ?? null,
            adx: adx[i] ?? null,
            sma20: sma20[i] ?? null,
            bbMiddle: bbMiddle[i] ?? null,
            bbUpper: bbUpper[i] ?? null,
            bbLower: bbLower[i] ?? null
        }));
    } catch (err) {
        console.error('Error during fetchAndAnalyze:', err);
        return []; // Return empty array on error
    }
}

// --- WebSocket Broadcast ---
async function broadcastAnalysis() {
    try {
        const analysis = await fetchAndAnalyze();
        const payload = JSON.stringify(analysis);
        wss.clients.forEach(client => {
            try {
                if (client.readyState === 1) { // WebSocket.OPEN === 1
                    client.send(payload);
                }
            } catch (sendErr) {
                console.error('Error sending data to client:', sendErr);
            }
        });
    } catch (err) {
        console.error('Analysis error:', err);
    }
}

// Broadcast every minute
setInterval(broadcastAnalysis, 60 * 1000);

// Initial push on server start and on new connection
wss.on('connection', async (ws) => {
    console.log('Client connected');
    try {
        const analysis = await fetchAndAnalyze();
        ws.send(JSON.stringify(analysis));
    } catch (err) {
        console.error('Error sending initial analysis:', err);
        ws.send(JSON.stringify({ error: 'Failed to fetch analysis' }));
    }
    ws.on('close', () => console.log('Client disconnected'));
    ws.on('error', (err) => console.error('WebSocket error:', err));
});

server.listen(PORT, () => {
    console.log(`Server running on https://localhost:${PORT}`);
});

