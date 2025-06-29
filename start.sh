#!/bin/bash

# Install Playwright browsers (needed for scraping)
python -m playwright install

# Then start the FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8000
