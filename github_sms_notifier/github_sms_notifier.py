import json

import re
from flask import Flask, flash, make_response
from flask.globals import request
from flask.templating import render_template
import requests
from twilio.rest import TwilioRestClient

PHONE_NUMBER_PATTERN = re.compile("^\\+?\\d{10,14}$")
PULL_REQUEST_OPENED = 'prOpened'
PULL_REQUEST_CLOSED = 'prClosed'
PULL_REQUEST_SYNCHRONIZE = 'prSynchronize'
PULL_REQUEST_REOPENED = 'prReopened'
REPOSITORIES = 'repositories'
REPOSITORY_PATTERN = re.compile("[A-Za-z0-9_\\.-]+/[A-Za-z0-9_\\.-]+")
SETTINGS_JSON_FILE_NAME = 'settings.json'
SETTINGS_TEMPLATE = 'settings.html'
TO_NUMBERS = 'toNumbers'
TWILIO_ACCOUNT_SID = 'twilioAccountSid'
TWILIO_AUTH_TOKEN = 'twilioAuthToken'
TWILIO_FROM_NUMBER = 'twilioFromNumber'

app = Flask(__name__)
short_urls = {}


@app.route('/')
def root():
    return 'Thank you for using github-sms-notifier!'


@app.route('/admin', methods=['GET'])
def config():
    settings = __read_settings()
    return render_template(SETTINGS_TEMPLATE, settings=settings)


@app.route('/admin', methods=['POST'])
def save_config():
    app.logger.debug(request.form)

    pull_request_closed_enabled = False
    if PULL_REQUEST_CLOSED in request.form:
        pull_request_closed_enabled = True

    pull_request_opened_enabled = False
    if PULL_REQUEST_OPENED in request.form:
        pull_request_opened_enabled = True

    pull_request_reopened_enabled = False
    if PULL_REQUEST_REOPENED in request.form:
        pull_request_reopened_enabled = True

    pull_request_synchronize_enabled = False
    if PULL_REQUEST_SYNCHRONIZE in request.form:
        pull_request_synchronize_enabled = True

    settings = {TWILIO_ACCOUNT_SID: request.form[TWILIO_ACCOUNT_SID].strip(),
                TWILIO_AUTH_TOKEN: request.form[TWILIO_AUTH_TOKEN].strip(),
                TWILIO_FROM_NUMBER: request.form[TWILIO_FROM_NUMBER].strip(),
                TO_NUMBERS: request.form[TO_NUMBERS].strip().split(), PULL_REQUEST_CLOSED: pull_request_closed_enabled,
                PULL_REQUEST_OPENED: pull_request_opened_enabled, PULL_REQUEST_REOPENED: pull_request_reopened_enabled,
                PULL_REQUEST_SYNCHRONIZE: pull_request_synchronize_enabled,
                REPOSITORIES: request.form[REPOSITORIES].strip().split()}

    errors = __validate_settings(settings)
    if errors:
        for error in errors:
            flash(error, category='error')
    else:
        with open(SETTINGS_JSON_FILE_NAME, 'w+') as settings_file:
            json.dump(settings, settings_file)
        flash("Settings saved!")

    return render_template(SETTINGS_TEMPLATE, settings=settings)


@app.route('/pullRequests', methods=['POST'])
def pull_requests():
    settings = __read_settings()
    if settings:
        content = json.loads(request.data)
        if 'pull_request' in content:
            client = TwilioRestClient(settings[TWILIO_ACCOUNT_SID], settings[TWILIO_AUTH_TOKEN])
            message = __build_sms_body(content)
            app.logger.debug(request.data)
            if message and not app.testing:
                numbers = settings[TO_NUMBERS]
                for number in numbers:
                    client.sms.messages.create(body=message, from_=settings[TWILIO_FROM_NUMBER], to=number)
        else:
            app.logger.warn("Not a pull request: {}".format(request.data))
    else:
        app.logger.warn("Cannot load settings.")
    return make_response("", 204)


def __build_sms_body(request_body):
    settings = __read_settings()
    message_prefix = 'Pull request #' + str(request_body['number'])
    message_suffix = request_body['repository']['full_name'] + ' ' + __get_short_url(
        request_body['pull_request']['html_url'])
    if request_body['action'] == 'opened':
        if settings[PULL_REQUEST_OPENED] and __is_supported_repository(settings.get(REPOSITORIES),
                                                                       request_body['repository']['full_name']):
            return message_prefix + ' was opened in ' + message_suffix
    elif request_body['action'] == 'closed':
        if settings[PULL_REQUEST_CLOSED] and __is_supported_repository(settings.get(REPOSITORIES),
                                                                       request_body['repository']['full_name']):
            return message_prefix + ' was closed in ' + message_suffix
    elif request_body['action'] == 'synchronize':
        if settings[PULL_REQUEST_SYNCHRONIZE] and __is_supported_repository(settings.get(REPOSITORIES),
                                                                            request_body['repository']['full_name']):
            return message_prefix + ' was synchronized in ' + message_suffix
    elif request_body['action'] == 'reopened':
        if settings[PULL_REQUEST_REOPENED] and __is_supported_repository(settings.get(REPOSITORIES),
                                                                         request_body['repository']['full_name']):
            return message_prefix + ' was reopened in ' + message_suffix
    else:
        return 'Unsupported action \'' + request_body['action'] + '\' occurred on pull request #' + str(
            request_body['number']) + ' in ' + message_suffix


def __get_short_url(url):
    if short_urls.get(url):
        return short_urls[url]

    payload = {'url': url}
    r = requests.post('http://git.io', data=payload)

    short_urls[url] = r.headers.get('Location')

    return short_urls[url]


def __is_supported_repository(repositories_settings, notification_repository):
    if not repositories_settings:
        return True
    for repository in repositories_settings:
        if notification_repository == repository:
            return True
    return False


def __is_valid_phone_number(phone_number):
    if PHONE_NUMBER_PATTERN.match(phone_number):
        return True
    else:
        return False


def __is_valid_repository_name(repository_name):
    if REPOSITORY_PATTERN.match(repository_name):
        return True
    else:
        return False


def __read_settings():
    settings = {}
    with open(SETTINGS_JSON_FILE_NAME, 'r+') as settings_file:
        try:
            settings = json.load(settings_file)
        except ValueError:
            app.logger.warning("Cannot load configuration.")
    return settings


def __validate_settings(settings):
    errors = []
    if not settings.get(TWILIO_ACCOUNT_SID):
        errors.append('Twilio Account Sid is required')
    if not settings.get(TWILIO_AUTH_TOKEN):
        errors.append('Twilio Auth Token is required')
    if not settings.get(TWILIO_FROM_NUMBER):
        errors.append('Twilio From Number is required')
    else:
        if not __is_valid_phone_number(settings.get(TWILIO_FROM_NUMBER)):
            errors.append("Invalid Twilio From Number: " + settings.get(TWILIO_FROM_NUMBER))
    if not settings.get(TO_NUMBERS):
        errors.append('Numbers to send SMS to is required')
    else:
        for to_number in settings.get(TO_NUMBERS):
            if not __is_valid_phone_number(to_number):
                errors.append("Invalid phone number: " + to_number)
    if settings.get(REPOSITORIES):
        for repository in settings.get(REPOSITORIES):
            if not __is_valid_repository_name(repository):
                errors.append("Invalid repository name format: " + repository)
    return errors


if __name__ == '__main__':
    app.secret_key = 'Uqtbl6HxgNWcJsuycuXtHQyR8ExiaNHm'
    app.debug = True
    app.run()
