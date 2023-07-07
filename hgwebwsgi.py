# An example WSGI for use with mod_wsgi, edit as necessar
# See https://mercurial-scm.org/wiki/modwsgi for more information

# Path to repo or hgweb config to serve (see 'hg help hgweb')
from mercurial import demandimport, commands
from wsgi_basic_auth import BasicAuth
from mercurial.hgweb import hgweb
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
from flask import Flask
import subprocess
import os
from dotenv import load_dotenv

project_folder = os.path.expanduser('~/.hgweb')
web_folder = os.path.join(project_folder, '_web')  # adjust as appropriate
repo_folder = os.path.join(project_folder, '_hg')
config = str.encode(os.path.join(web_folder, 'hgweb.config'))
load_dotenv(os.path.join(web_folder, '.env'))

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
style = gitweb
pygments_style = colorful
highlightonlymatchfilename = False

[paths]
/ = %s/_hg/*
""" % format(project_folder)

default_page = """
<html>
<body>
<h1>simple site</h1>
<p><a href="/">home</a></p>
<p><a href="/hg">hg</a></p>
</body>
</html>
"""

with open(config, 'w') as f:
    f.write(hgconfig)

hgapp = hgweb(config)
api = Flask(__name__)


@api.route('/')
def hello_world():
    return "<p>Hello, World!</p>"


@api.route('/hginit/<string:dest>')
def api_hginit(dest):
    commands.init(hgapp.ui, str.encode(os.path.join(repo_folder, dest)))
    hgapp.refresh()
    return dest


@api.route('/rm/<string:dest>')
def api_rm(dest):
    subprocess.call(['rm', '-rf', os.path.join(repo_folder, dest)])
    hgapp.refresh()
    return dest


application = DispatcherMiddleware(
    Response(default_page, status=200, headers={'Content-Type': 'text/html'}),
    {
        '/hg': hgapp,
        '/api': api
    })
application = BasicAuth(application)
