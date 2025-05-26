import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';

const App = () => {
    const [marketData, setMarketData] = useState([]);
    const [wsError, setWsError] = useState(null);

    useEffect(() => {
        const ws = new WebSocket('wss://your-server-domain:3000'); // Ensure you use 'wss://' for secure WebSocket

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
            }
        };

        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            setWsError('WebSocket connection error. Please try again later.');
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed');
        };

        return () => {
            ws.close(); // Close WebSocket connection on cleanup
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