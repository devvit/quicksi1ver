# An example WSGI for use with mod_wsgi, edit as necessar
# See https://mercurial-scm.org/wiki/modwsgi for more information

# Path to repo or hgweb config to serve (see 'hg help hgweb')
from mercurial import demandimport, commands
from wsgi_basic_auth import BasicAuth
from mercurial.hgweb import hgweb

# from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask, request, redirect, url_for
import shutil
import os
from dotenv import load_dotenv
from flask import render_template_string
from flask_turbolinks import turbolinks
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


class CustomBasicAuth(BasicAuth):
    """
    重写 BasicAuth，Query 优先级最高，没传则回退到父类。
    """

    def is_authorized(self, request):
        # 1. 检查用户是否传了 Query 参数
        username = request.GET.get("u")
        password = request.GET.get("p")

        if username is not None or password is not None:
            # 只要传了 query，就以 query 的验证结果为准
            return self._users.get(username) == password

        # 2. 如果没传 query，直接交给父类（父类会自己判断路径包含/排除以及 Header）
        return super(CustomBasicAuth, self).is_authorized(request)


project_folder = os.path.expanduser("~/.hgweb")
web_folder = os.path.join(project_folder, "_web")  # adjust as appropriate
repo_folder = os.path.join(project_folder, "_hg")
config = str.encode(os.path.join(web_folder, "hgweb.config"))
load_dotenv(os.path.join(web_folder, ".env"))
os.makedirs(os.path.join(project_folder, "_files"), exist_ok=True)

# Uncomment and adjust if Mercurial is not installed system-wide
# (consult "installed modules" path from 'hg debuginstall'):
# import sys; sys.path.insert(0, "/path/to/python/lib")

# Uncomment to send python tracebacks to the browser if an error occurs:
# import cgitb; cgitb.enable()

# enable demandloading to reduce startup time
demandimport.enable()

hgconfig = """
[extensions]
highlight =

[web]
encoding = "UTF-8"
baseurl = /hg
allow_push = *
push_ssl = False
allow_archive = gz, zip
style = monoblue
pygments_style = colorful
highlightonlymatchfilename = False

[paths]
/ = %s/_hg/*
""" % format(project_folder)

with open(config, "w") as f:
    f.write(hgconfig)

hgapp = hgweb(config)
myapp = Flask(__name__)
turbolinks(myapp)
myapp.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI")
db = SQLAlchemy(myapp)


def render_with_layout(content, **context):
    layout = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Project Manager</title>
    <link href="https://testingcf.jsdelivr.net/npm/bootstrap@5.3.6/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://testingcf.jsdelivr.net/npm/turbolinks@5.2.0/dist/turbolinks.min.js"></script>
    <script src="https://testingcf.jsdelivr.net/npm/marked@15.0.12/marked.min.js"></script>
    </head>
    <body>
      <div class="container-fluid">
          <h1>🗂 Project Manager<sup>
          <a href="/" data-turbolinks="false">HOME</a>
          <a href="/hg" data-turbolinks="false">HG</a>
          </sup></h1>
          {{ content|safe }}
      </div>
    </body></html>
    """
    inner = render_template_string(content, **context)
    return render_template_string(layout, content=inner)


@myapp.route("/")
def index():
    content = """
    <h1>empty app</h1>
    """
    return render_with_layout(content)


with myapp.app_context():
    # db.drop_all()
    db.create_all()


@myapp.route("/api/hginit/<string:dest>")
def api_hginit(dest):
    commands.init(hgapp.ui, str.encode(os.path.join(repo_folder, dest)))
    hgapp.refresh()
    return dest


@myapp.route("/api/rm/<string:dest>")
def api_rm(dest):
    shutil.rmtree(os.path.join(repo_folder, dest), ignore_errors=True)
    hgapp.refresh()
    return dest


application = CustomBasicAuth(DispatcherMiddleware(myapp, {"/hg": hgapp}))

# if __name__ == "__main__":
#     run_simple("0.0.0.0", 8080, application, use_debugger=True)
