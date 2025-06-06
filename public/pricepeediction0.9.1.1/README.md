# Cryptocurrency Price Prediction Dashboard

This project is a Cryptocurrency Price Prediction Dashboard that provides users with insights into cryptocurrency price trends and predictions. It utilizes various technical indicators to analyze price data and generate trading signals.

## Project Structure

- **public/index.html**: Contains the HTML structure for the dashboard, featuring a combined graph and sections for market data and predictions.
- **server-key.pem**: SSL key used for secure connections.
- **server-cert.pem**: SSL certificate used for secure connections.
- **priceprediction.py**: Python script for processing cryptocurrency price data. It includes functions for calculating MACD and DMI/ADX indicators, validating data, preprocessing, training a linear regression model, and generating trading signals.
- **setup.sh**: Shell script that installs the repository and ensures the inclusion of necessary files.

## Installation

To set up the project, run the following command in your terminal:

```bash
bash setup.sh
```

This will install the required dependencies and ensure that the SSL certificates, `index.html`, and `priceprediction.py` are included in the project.

## Usage

1. Start the server to serve the dashboard.
2. Input cryptocurrency price data into the `priceprediction.py` script to receive predictions and trading signals.
3. View the dashboard in your web browser to visualize the data and predictions.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License.