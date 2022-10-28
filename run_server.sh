python3.10 -m venv
./venv/bin/pip3 install -r requirements.txt
export PYTHONPATH="$PWD"
./venv/bin/python3.10 -m uvicorn app.main:app --root-path="$PWD"
