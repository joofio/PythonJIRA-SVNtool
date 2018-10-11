from bottle import run, Bottle, request
import svn.local
import itertools
import pandas
import datetime
from jira import JIRA
import json


app = Bottle()


@app.route('/')
def index():
    return """<!doctype html>
<html lang="en">

<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <!-- styles -->
    <link href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    <title>SVN to Excel</title>
</head>

<body>
    <div class="container">
        <div class="jumbotron">
            <h1 class="display-3">Svn To Excel</h1>
            <p class="lead">This is a simple app to collect all packages with a certain tag</p>
            <hr class="my-2">
            <p>It uses your local repository and your jira password and username</p>
        </div>
        <div class="row">
            <div class="col-md-10 col-md-offset-2">
                <form method="POST" action="/">
                    <div class="form-group row">
                            <label for="inputEmail3" class="col-sm-1 col-form-label">Email</label>
                            <div class="col-sm-4">
                                <input type="email" class="form-control" id="inputEmail3" placeholder="Email" name='id'>
                            </div>
                            <label for="inputEmail3" class="col-sm-1 col-form-label">password</label>
                            <div class="col-sm-3">
                                <input type="password" class="form-control" id="inputpassword3" placeholder="password" name='pass'>
                            </div>
                    </div>
                    <div class="form-group row">
                            <label for="inputEmail4" class="col-sm-1 col-form-label">Jira Issue</label>
                            <div class="col-sm-4">
                                <input type="text" class="form-control" id="inputEmail3" placeholder="Issue" name='issue'>
                            </div>
                            <label for="inputEmail4" class="col-sm-1 col-form-label">Date</label>
                            <div class="col-sm-3">
                                <input type="date" class="form-control" id="inputpassword3" placeholder="date" name='date'>
                            </div>
                    </div>
                    <div class="form-group row">
                        <div class="col-sm-10 offset-sm-2">
                            <button type="submit" class="btn btn-primary">Submit</button>
                        </div>
                    </div>
                </form>
            </div>
        </div>

    </div>
    </div>
    </div>
    <!-- scripts -->
    <script src="//code.jquery.com/jquery-1.11.3.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
</body>

</html>
"""


@app.route('/', method='POST')
def process():
    """Handle the form submission"""
    username = request.forms.get('id')
    password = request.forms.get('pass')
    tag_main_issue = request.forms.get('issue')
    time_stamp = request.forms.get('date')

    with open('includes.json', 'r') as f:
        config_data = json.load(f)
    localClient = config_data['svnLocalClient']
    jiraLink = config_data['JiraLink']
    change_list = []
    merged = []
    username = username.split('@', 1)[0]
    year = int(time_stamp[:4])
    month = int(time_stamp[5:7])
    day = int(time_stamp[8:10])
    date = datetime.datetime(year, month, day)
    l = svn.local.LocalClient(localClient)
    authed_jira = JIRA(jiraLink, basic_auth=(username, password))

    issue = authed_jira.issue(tag_main_issue)  # 16014
    links = issue.fields.issuelinks
    issues_to_search = []

    for link in links:
        if hasattr(link, "outwardIssue"):
            outwardIssue = link.outwardIssue
        if hasattr(link, "inwardIssue"):
            inwardIssue = link.inwardIssue
            issues_to_search.append(inwardIssue.key.replace('-', '_'))

    issues_to_search.append(tag_main_issue.replace('-', '_'))
    for issue in issues_to_search:

        for e in l.log_default(timestamp_from_dt=date, changelist=True):
            if e.msg is not None and issue in e.msg:
                # print e.changelist
                change_list.append(e.changelist)

        merged = list(itertools.chain.from_iterable(change_list))

        change_list_final_spec = []
        change_list_final_body = []
        change_list_final_other = []
        for item in merged:

            if '.spc' in item[1] and item not in change_list_final_spec:
                change_list_final_spec.append(item)
            elif '.bdy' in item[1] and item not in change_list_final_body:
                change_list_final_body.append(item)
            elif '.bdy' not in item[1] and '.spc' not in item[1] and item not in change_list_final_other:
                change_list_final_other.append(item)
            else:
                continue

    max_length = max(len(change_list_final_spec), len(
        change_list_final_body), len(change_list_final_other))

    while max_length > len(change_list_final_spec):
        change_list_final_spec.append('')

    while max_length > len(change_list_final_body):
        change_list_final_body.append('')

    while max_length > len(change_list_final_other):
        change_list_final_other.append('')

    data_frame = pandas.DataFrame(
        {'body': change_list_final_body, 'spec': change_list_final_spec, 'other': change_list_final_other})

    data_frame.to_excel('/svn_' + tag_main_issue + '.xlsx')

    message = '<h1> Your file is ready</h1> '

    return message


run(app, host='localhost', port=8080)
