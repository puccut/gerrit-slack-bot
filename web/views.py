from flask import Flask, request, session, render_template, redirect, url_for, flash, g
from croniter import croniter
import uwsgi
import slack
from database import Database, Crontab
from bot import CronTime, MuleMessage
from . import app, slack_app, slack_api, Alert


@app.before_request
def before_request():
    g.db = Database()


@app.after_request
def after_request(response):
    g.db.close()
    return response


@app.route('/')
def index():
    return render_template('index.html', crontabs=g.db.load_all_crontabs())


@app.route('/new', methods=['GET'])
def new():
    return render_template('new.html', invalid_form=session.get('invalid_form', None))


@app.route('/new', methods=['POST'])
def save_new_to_db():
    if not is_form_valid():
        session['invalid_form'] = request.form
        return redirect(url_for('new'))

    f = request.form
    # TODO: cache the channels.info result for faster lookup
    channel_id = slack_api.get_channel_id(f['channel_name'])
    crontab = Crontab(None, f['channel_name'], channel_id, f['gerrit_query'], f['crontab'])
    g.db.save_crontab(crontab)

    session.clear()
    flash(f'Config added for {crontab.channel_name}', Alert.SUCCESS)
    uwsgi.mule_msg(MuleMessage.RELOAD)
    return redirect('/')


@app.route('/edit/<int:crontab_id>', methods=['GET', 'POST'])
def edit(crontab_id):
    crontab = g.db.load_crontab(crontab_id)

    if request.method == 'POST' and is_form_valid():
        channel_name = request.form['channel_name']
        gerrit_query = request.form['gerrit_query']
        crontab_entry = request.form['crontab']
        crontab = Crontab(crontab_id, channel_name, crontab.channel_id, gerrit_query, crontab_entry)
        g.db.update_crontab(crontab)
        flash('Updated succesfully.', Alert.SUCCESS)
        uwsgi.mule_msg(MuleMessage.RELOAD)

    return render_template('edit.html', crontab=crontab)


def is_form_valid():
    channel_name = request.form['channel_name']
    gerrit_query_data = request.form['gerrit_query']
    crontab_data = request.form['crontab']

    is_valid = True

    if not channel_name.startswith(('@', '#')):
        flash('The channel name should start with @ or #.')
        is_valid = False

    if not gerrit_query_data:
        flash('You need to have a gerrit query.', Alert.DANGER)
        is_valid = False

    if not crontab_data:
        flash('You need to fill out the crontab entry.', Alert.DANGER)
        is_valid = False

    elif not croniter.is_valid(crontab_data):
        flash('Invalid crontab syntax.', Alert.DANGER)
        is_valid = False

    return is_valid


@app.route('/delete/<int:crontab_id>', methods=['POST'])
def delete(crontab_id):
    crontab = g.db.load_crontab(crontab_id)
    g.db.delete_crontab(crontab_id)
    flash(f'Succesfully removed bot from {crontab.channel_name}', Alert.SUCCESS)
    uwsgi.mule_msg(MuleMessage.RELOAD)
    return redirect('/')


@app.route('/slack-oauth')
def slack_oauth():
    # If the states don't match, the request come from a third party and the process should be aborted.
    # See https://api.slack.com/docs/slack-button
    if request.args['state'] != session['oauth_state']:
        return 'Invalid state. You have been logged and will be caught.'

    error = request.args.get('error')
    if error == 'access_denied':
        flash('Access denied - Request cancelled', Alert.WARNING)
        return redirect('/')
    elif error is not None:
        flash('Unknown error - try again', Alert.DANGER)
        return redirect('/')

    session['webhook_data'] = slack_app.request_oauth_token(request.args['code'])

    return redirect(url_for('new'))


@app.route('/usage')
def usage():
    return render_template('usage.html')