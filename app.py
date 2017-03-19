import hmac
import json
import time
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user
from wtforms import Form, BooleanField, StringField, PasswordField, validators

from aws_hooks import build_client, launch_node, get_newest_instance
from ansible_hooks import run_play

app = Flask(__name__)
app.secret_key = os.urandom(30).hex()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"


class AdminUser(UserMixin):
    def __init__(self, secret):
        self.id = os.urandom(15).hex()
        self.name = "Super-Admin"
        self.secret = secret

    def pass_digest(self):
        return 'admin'+self.secret


with open('files/aws_creds.json', 'r') as f:
    secret = json.loads(f.read())['flask_auth']


super_admin = AdminUser(secret)
Users = { super_admin.get_id(): super_admin }


@login_manager.user_loader
def load_user(user_id):
    print('trying to load user: %s' % user_id)
    return Users.get(user_id)


def get_user_check_passphrase(form):
    uname, passphrase = form.username.data, form.passphrase.data
    if hmac.compare_digest(uname+passphrase, super_admin.pass_digest()):
        return super_admin
    else:
        return None


ec2 = build_client()


def wait_for_start(instance):
    # Actually measure this mofo
    print('Waiting for instance to start')
    if instance.state == 'running':
        return
    time.sleep(60)


def deploy_globaleaks_instance():
    instance = launch_node(ec2)
    #instance = get_newest_instance(ec2)

    wait_for_start(instance)
    print('Instance started', instance)

    run_play(instance.public_ip_address)


class RegistrationForm(Form):
    hostname = StringField('Project name', [validators.Length(min=6, max=35)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])


class LoginForm(Form):
    username = StringField('', [validators.Length(min=4, max=25)])
    passphrase = PasswordField('', [validators.Length(min=4)])


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if form.validate():
        user = get_user_check_passphrase(form)
        if user is None:
            flash('Bad username or passphrase')
        else:
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('home'))
    return render_template('login.html', form=form)

login_manager.login_view = '/login'

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        print(form.username.data, form.email.data,
                form.hostname.data)
        deploy_globaleaks_instance()
        flash('Instance launched successfully at %s' % datetime.now(), 'success')

    instances = ec2.instances.all()

    return render_template('index.html', reg_form=form, instances=instances)


if __name__ == '__main__':
    #deploy_globaleaks_instance()
    app.run(debug=True)
