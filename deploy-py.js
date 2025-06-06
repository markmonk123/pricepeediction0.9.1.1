import { execSync, spawn } from 'child_process';
import path from 'path';

// 1. Check Python is installed
try {
    execSync('python3 --version', { stdio: 'inherit' });
} catch {
    console.error('Python3 is not installed or not in PATH.');
    process.exit(1);
}

// 2. (Optional) Install Python dependencies
try {
    execSync('pip3 install -r requirements.txt', { stdio: 'inherit' });
} catch {
    console.warn('No requirements.txt found or pip install failed. Skipping dependency install.');
}

// 3. Run priceprediction.py
const scriptPath = path.resolve('./priceprediction.py');
const py = spawn('python3', [scriptPath], { stdio: 'inherit' });

py.on('close', (code) => {
    if (code === 0) {
        console.log('priceprediction.py ran successfully.');
    } else {
        console.error(`priceprediction.py exited with code ${code}`);
    }
});