#

# set -a; source ~/.hgall/web/.env; set +a
source .env
export DB_URI='mysql+pymysql://root@localhost/pm_dev'
gunicorn -b 0.0.0.0:1433 --reload --log-level debug hgwebwsgi:application
