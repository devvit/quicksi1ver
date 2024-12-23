# An example WSGI for use with mod_wsgi, edit as necessar
# See https://mercurial-scm.org/wiki/modwsgi for more information

# Path to repo or hgweb config to serve (see 'hg help hgweb')
from mercurial import demandimport, commands
from wsgi_basic_auth import BasicAuth
from mercurial.hgweb import hgweb
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
from flask import Flask, render_template_string, url_for
import shutil
import os
from dotenv import load_dotenv
from flask_cloudy import Storage

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

default_page = """
<!DOCTYPE html>
<html>
<head>
<style>
* { font-family: sans-serif; }
</style>
</head>
<body>

<h1>WELCOME</h1>
<p><a href="/">HOME</a></p>
<p><a href="/hg">HG</a></p>
<p><a href="/my">FILES</a></p>

</body>
</html>
"""

index_page = """
<!DOCTYPE html>
<html>
<head lang="en">
    <meta charset="UTF-8">
    <title>Flask-Cloudy</title>
</head>
<body>

<h1>Flask-Cloudy</h1>


<form action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
    Select image to upload:
    <input type="file" name="file" id="fileToUpload"> <br>
    <input type="submit" value="Upload File" name="submit">
</form>

<hr>

<h3>List of files available on the storage:</h3>

<table>
    <thead>
        <th>Name</th>
        <th>Size</th>
    </thead>
    <tbody>
        {% for obj in storage %}
        <tr>
            <td><a href="{{ url_for('view', object_name=obj.name) }}">{{ obj.name }}</a></td>
            <td>{{ obj.size }} bytes</td>
        </tr>
        {% endfor %}
    </tbody>

</table>

</body>
</html>
"""

view_page = """
<!DOCTYPE html>
<html>
<head lang="en">
    <meta charset="UTF-8">
    <title>Flask-Cloudy</title>
</head>
<body>

<h1>Flask-Cloudy: View File</h1>
<a href="{{ url_for('index') }}"><- Home</a>
<br> <br>

Name: {{ obj.name }} <br><br>
Size: {{ obj.size }} bytes <br><br>

Short url: {{ obj.short_url }} <br><br>

View file: <a href="{{ obj.url }}">{{ obj.url }}</a> <br><br>

{% set download_url = obj.download_url() %}
Download: <a href="{{ download_url }}">{{ download_url }}</a> <br><br>
</body>
</html>
"""

with open(config, "w") as f:
    f.write(hgconfig)

hgapp = hgweb(config)
myapp = Flask(__name__)
myapp.config.update(
    {
        "STORAGE_PROVIDER": "LOCAL",
        "STORAGE_KEY": "",
        "STORAGE_SECRET": "",
        "STORAGE_CONTAINER": os.path.join(project_folder, "_files"),
        "STORAGE_SERVER": True,
        # "STORAGE_SERVER_URL": "/files",
    }
)
storage = Storage()
storage.init_app(myapp)


@myapp.route("/")
def hello_world():
    return render_template_string(index_page, storage=storage)


@myapp.route("/view/<path:object_name>")
def view(object_name):
    obj = storage.get(object_name)
    return render_template_string(view_page, obj=obj)


@myapp.route("/hginit/<string:dest>")
def api_hginit(dest):
    commands.init(hgapp.ui, str.encode(os.path.join(repo_folder, dest)))
    hgapp.refresh()
    return dest


@myapp.route("/rm/<string:dest>")
def api_rm(dest):
    shutil.rmtree(os.path.join(repo_folder, dest), ignore_errors=True)
    hgapp.refresh()
    return dest


application = DispatcherMiddleware(
    Response(default_page, status=200, headers={"Content-Type": "text/html"}),
    {"/hg": hgapp, "/my": myapp},
)
application = BasicAuth(application)
