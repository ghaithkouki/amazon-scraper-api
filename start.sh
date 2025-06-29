#!/bin/bash

# Install Playwright browsers
playwright install

# Start your FastAPI or other app
uvicorn main:app --host 0.0.0.0 --port 8000
