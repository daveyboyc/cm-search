web: gunicorn capacity_checker.wsgi --log-file -
api: cd cmr-api && uvicorn app.main:app --host=0.0.0.0 --port=$PORT
