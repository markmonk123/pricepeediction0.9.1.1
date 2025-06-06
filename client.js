import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';

const App = () => {
    const [marketData, setMarketData] = useState([]);
    const [wsError, setWsError] = useState(null);

    useEffect(() => {
        // Use environment variable for WebSocket URL, default to localhost:9000
        const wsUrl = process.env.REACT_APP_WEBSOCKET_URL || 'wss://127.0.0.1:9000';
        let ws; // Declare ws outside the try block

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('Connected to WebSocket');
                setWsError(null);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setMarketData((prevData) => [...prevData, data]); // Append new data
                    console.log('Received market data:', data);
                } catch (err) {
                    console.error('Error parsing WebSocket data:', err);
                    setWsError('Error parsing data from WebSocket.');
                }
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                setWsError(`WebSocket connection error: ${err.message}.  Check server and certificate.`);
            };

            ws.onclose = () => {
                console.log('WebSocket connection closed');
                setWsError('WebSocket connection closed.');
            };
        } catch (error) {
            console.error('WebSocket initialization error:', error);
            setWsError(`Failed to initialize WebSocket: ${error.message}`);
            return; // Prevent further execution if WebSocket fails to initialize
        }

        return () => {
            if (ws) {
                ws.close(); // Close WebSocket connection on cleanup
            }
        };
    }, []);

    const chartData = {
        labels: marketData.map(data => data.timestamp),
        datasets: [{
            label: 'Price Data',
            data: marketData.map(data => data.close),
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 2,
        }]
    };

    return (
        <div>
            <h1>Cryptocurrency Price Prediction</h1>
            {wsError && <div style={{color: 'red'}}>{wsError}</div>}
            <Line data={chartData} />
        </div>
    );
};

export default App;