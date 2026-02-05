**Stock Analysis App Walkthrough**

**Overview**
This application provides comprehensive stock analysis for Nasdaq and IDX (Indonesia) markets. It features:
- Real-time Price & Profile: Fetched from Yahoo Finance.
- Technical Analysis: Moving Averages (10/20/50/100/200), RSI, Stochastic.
- Pattern Recognition: Detects Candle Patterns (Doji, Hammer, Engulfing) and Trend signals (Golden/Death Cross).
- Recommendation Engine: Generates a Buy/Sell/Neutral rating based on a weighted score of indicators.
- Fundamentals: Displays Quarterly Revenue, Net Income, and Op. Expenses, plus PER and PBV ratios.
- Interactive Charts: Professional-grade candlestick charts powered by Lightweight Charts.

**Prerequisites**
Python 3.10+ (Already installed)

**How to Run Locally**
1. Verify Dependencies Ensure all requirements are installed: _pip install -r backend/requirements.txt_
2. Start the Server Run the following command from the project root (d:\POC\AntiGravity\stocks): _python -m uvicorn backend.main:app --reload_
3. Access the App Open your browser and navigate to: http://127.0.0.1:8000
4. Using the App
- Search: Enter a symbol in the search bar (e.g., AAPL for Apple, BBCA.JK for Bank Central Asia).
- Data: The app will load charts, technical indicators, and fundamentals automatically.


**Cloud Deployment (Free Tier)**
This application is designed to be lightweight and stateless, making it suitable for free tier deployments like Render or Railway.
Deploying to Render.com (Free Web Service)
1. Push to GitHub: Commit this code to a GitHub repository.
2. Create New Web Service: In Render dashboard, select "New Web Service" and connect your repo.
3. Configuration:
  - Runtime: Python 3
  - Build Command: pip install -r backend/requirements.txt
  - Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
4. Deploy: Click create. Your app will be live at https://your-app-name.onrender.com.


**Docker Deployment**
1. Hubungkan repositori GitHub Anda.
2. Pilih Build Type: Docker.
3. Set Port ke 8000.
4. Deploy.


**Project Structure**
- backend/main.py : Core API and static file handling.
- backend/analysis.py : Logic for Technical Indicators and Pattern Recognition.
- backend/static/ : Contains the Frontend (HTML, CSS, JS).
index.html: UI Layout.
app.js: Application logic (Vue.js).
style.css: Custom styling.
