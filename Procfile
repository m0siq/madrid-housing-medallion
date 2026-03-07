web: python scripts/seed_railway_db.py && uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
dashboard: streamlit run app/dashboard/streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
