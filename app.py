import time
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from wtforms import Form, BooleanField, StringField, validators

from aws_hooks import build_client, launch_node, get_newest_instance
from ansible_hooks import run_play

app = Flask(__name__)
app.secret_key = str(os.urandom(20))
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
    # From flask documentation
    hostname = StringField('Project name', [validators.Length(min=6, max=35)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    accept_tos = BooleanField('I accept the TOS', [validators.DataRequired()])


@app.route('/', methods=['GET', 'POST'])
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
