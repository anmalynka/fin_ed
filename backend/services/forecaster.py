import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ForecastEngine:
    def __init__(self, ticker):
        self.ticker = ticker

    def run_forecast(self):
        stock = yf.Ticker(self.ticker)
        df = stock.history(period="1y")
        if len(df) < 50: return None
        
        prices = df['Close'].values
        dates = df.index
        
        # 1. Recent Momentum (Last 60 days)
        recent_df = df.tail(60)
        recent_x = np.arange(len(recent_df))
        recent_y = recent_df['Close'].values
        slope, intercept = np.polyfit(recent_x, recent_y, 1)
        
        # 2. Volatility factor
        volatility = recent_df['Close'].std()
        
        # 3. Project 1 Year
        future_x = np.arange(len(recent_y), len(recent_y) + 252)
        # Primary Hybrid Trend (Momentum + Sinusoidal Seasonality)
        # Seasonality is based on a 252-day business cycle
        seasonality = np.sin(2 * np.pi * future_x / 252) * (volatility * 2)
        trend = slope * future_x + intercept
        
        hybrid_forecast = trend + seasonality + np.random.normal(0, volatility * 0.5, 252)
        
        # Baseline (Simple Trend)
        baseline = trend
        
        # 4. Dates
        last_date = dates[-1]
        forecast_dates = [(last_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 253)]
        
        # Results
        history_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(dates[-100:], prices[-100:])]
        forecast_points = [{"date": d, "price": round(float(p), 2)} for d, p in zip(forecast_dates, hybrid_forecast)]
        baseline_points = [{"date": d, "price": round(float(p), 2)} for d, p in zip(forecast_dates, baseline)]

        return {
            "history": history_points,
            "hybrid": forecast_points,
            "baseline": baseline_points
        }
