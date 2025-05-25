javascript
import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';

const App = () => {
    const [marketData, setMarketData] = useState([]);

    useEffect(() => {
        const ws = new WebSocket('wss://your-server-domain:3000'); // Ensure you use 'wss://' for secure WebSocket

        ws.onopen = () => {
            console.log('Connected to WebSocket');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMarketData((prevData) => [...prevData, data]); // Append new data
            console.log('Received market data:', data);
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
            <Line data={chartData} />
        </div>
    );
};

export default App;