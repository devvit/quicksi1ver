#

# set -a; source ~/.hgall/web/.env; set +a
source .env
gunicorn -b 0.0.0.0:7777 hgwebwsgi:application
