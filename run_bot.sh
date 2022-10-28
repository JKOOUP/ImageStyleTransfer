python3.10 -m venv venv
./venv/bin/pip3 install -r requirements.txt
export PYTHONPATH="$PWD"
./venv/bin/python3.10 ./tg_bot/bot.py