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


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship("Task", backref="project", cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.TEXT, nullable=True)
    done = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


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
    projects = Project.query.order_by(Project.created.desc()).all()
    content = """
    <ul>
      {% for p in projects %}
        <li>
          <a href="{{ url_for('project', pid=p.id) }}">{{ p.name }}</a>
          [<a href="{{ url_for('delete_project', pid=p.id) }}" onclick="return confirm('Delete project?')">x</a>]
        </li>
      {% endfor %}
    </ul>
    <h2>Add Project</h2>
    <form method="post" action="{{ url_for('add_project') }}">
        <input name="name" placeholder="Project Name">
        <button type="submit">Add</button>
    </form>
    """
    return render_with_layout(content, projects=projects)


@myapp.route("/add_project", methods=["POST"])
def add_project():
    name = request.form["name"]
    if name.strip():
        db.session.add(Project(name=name))
        db.session.commit()
    return redirect(url_for("index"))


@myapp.route("/delete_project/<int:pid>")
def delete_project(pid):
    proj = Project.query.get_or_404(pid)
    db.session.delete(proj)
    db.session.commit()
    return redirect(url_for("index"))


@myapp.route("/project/<int:pid>")
def project(pid):
    proj = Project.query.get_or_404(pid)
    tasks = Task.query.filter_by(project_id=pid).order_by(Task.created.desc()).all()
    content = """
    <a href="{{ url_for('index') }}">← Back</a>
    <h2>{{ proj.name }}</h2>
    <ul>
      {% for t in tasks %}
        <li>{{ '✓' if t.done else '✗' }} {{ t.title }}
          [<a href="{{ url_for('toggle_task', tid=t.id) }}">Toggle</a>]
          [<a href="{{ url_for('task_view', tid=t.id) }}">Edit</a>]
          [<a href="{{ url_for('delete_task', tid=t.id) }}" onclick="return confirm('Delete task?')">x</a>]
        </li>
      {% endfor %}
    </ul>
    <h3>Add Task</h3>
    <form method="post" action="{{ url_for('add_task', pid=proj.id) }}">
        <input name="title" placeholder="Task title">
        <button type="submit">Add</button>
    </form>
    """
    return render_with_layout(content, proj=proj, tasks=tasks)


@myapp.route("/add_task/<int:pid>", methods=["POST"])
def add_task(pid):
    title = request.form["title"]
    if title.strip():
        db.session.add(Task(project_id=pid, title=title))
        db.session.commit()
    return redirect(url_for("project", pid=pid))


@myapp.route("/task/<int:tid>")
def task_view(tid):
    task = Task.query.get_or_404(tid)
    content = """
    <a href="{{ url_for('project', pid=task.project.id) }}">← Back to Project</a>
    <form method="post" action="{{ url_for('update_task', tid=task.id) }}">
        <button type="submit">Update</button><br>
        <textarea id="content" name="content" cols="80" rows="30">{{ task.content }}</textarea><br>
        <div id="html-preview" style="position:absolute; top: 100px; left: 720px;"></div>
        <label>Title:</label><br>
        <input name="title" value="{{ task.title }}"><br><br>
        <label>Status:</label><br>
        <select name="done">
            <option value="0" {% if not task.done %}selected{% endif %}>Not Done</option>
            <option value="1" {% if task.done %}selected{% endif %}>Done</option>
        </select><br><br>
    </form>
    <script>
        function preview() {
            const markdownContent = document.getElementById('content').value;
            const htmlPreview = document.getElementById('html-preview');
            htmlPreview.innerHTML = marked.parse(markdownContent);
        }
        document.getElementById('content').addEventListener('input', preview);
        preview();
    </script>
    """
    return render_with_layout(content, task=task)


@myapp.route("/update_task/<int:tid>", methods=["POST"])
def update_task(tid):
    task = Task.query.get_or_404(tid)
    task.title = request.form["title"]
    task.content = request.form["content"]
    task.done = request.form.get("done") == "1"
    db.session.commit()
    return redirect(url_for("task_view", tid=tid))


@myapp.route("/toggle_task/<int:tid>")
def toggle_task(tid):
    task = Task.query.get_or_404(tid)
    task.done = not task.done
    db.session.commit()
    return redirect(url_for("project", pid=task.project_id))


@myapp.route("/delete_task/<int:tid>")
def delete_task(tid):
    task = Task.query.get_or_404(tid)
    pid = task.project_id
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("project", pid=pid))


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


application = BasicAuth(DispatcherMiddleware(myapp, {"/hg": hgapp}))

# if __name__ == "__main__":
#     run_simple("0.0.0.0", 8080, application, use_debugger=True)
