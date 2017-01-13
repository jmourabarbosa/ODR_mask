# this file imports custom routes into the experiment server

from flask import Blueprint, render_template, request, jsonify, Response, abort, current_app
from jinja2 import TemplateNotFound
from functools import wraps
from sqlalchemy import or_, create_engine, MetaData, Table

from psiturk.psiturk_config import PsiturkConfig
from psiturk.experiment_errors import ExperimentError
from psiturk.user_utils import PsiTurkAuthorization, nocache

# # Database setup
from psiturk.db import db_session, init_db, engine
from psiturk.models import Participant
from json import dumps, loads
from numpy import loadtxt
import random
from pickle import load
import json
from matplotlib.mlab import find
from numpy import argsort,nan


# trial type
TASK=0
TEST=1

# load the configuration options
config = PsiturkConfig()
config.load_config()
myauth = PsiTurkAuthorization(config)  # if you want to add a password protect route use this

# explore the Blueprint
custom_code = Blueprint('custom_code', __name__, template_folder='templates', static_folder='static')

with open("all_trials.pickle") as f:
    all_trials = load(f)



###########################################################
#  serving warm, fresh, & sweet custom, user-provided routes
#  add them here
###########################################################

#----------------------------------------------
# example custom route
#----------------------------------------------
@custom_code.route('/my_custom_view')
def my_custom_view():
	current_app.logger.info("Reached /my_custom_view")  # Print message to server.log for debugging 
	try:
		return render_template('custom.html')
	except TemplateNotFound:
		abort(404)

#----------------------------------------------
# example using HTTP authentication
#----------------------------------------------
@custom_code.route('/my_password_protected_route')
@myauth.requires_auth
def my_password_protected_route():
	try:
		return render_template('custom.html')
	except TemplateNotFound:
		abort(404)

#----------------------------------------------
# example accessing data
#----------------------------------------------
# filter subjects with no real experiment

# returns last session
def get_session(data):

    session={}
    session["phase"] = nan
    session["total_reward"] = nan
    session["trial_number"] = nan

    s=json.dumps(session)

    for i in range(1,len(data)):
        if "session" in data[-i].keys():
            s=data[-i]["session"]
            break

    session = json.loads(s)
    session["total_reward"] = round(session["total_reward"],2)

    return session

@custom_code.route('/view_data')
@myauth.requires_auth
def list_my_data():
        users = Participant.query.all()


        table_name = 'swaps'
        data_column_name = 'datastring'
        # boilerplace sqlalchemy setup
        metadata = MetaData()
        metadata.bind = engine
        table = Table(table_name, metadata, autoload=True)
        # make a query and loop through
        s = table.select()
        rows = s.execute()

        all_trials  = {}
        hits=[]
        trials = []
        workerIDs =[]
        sessions = []
        phase = []
        for r in rows:
            if r["datastring"]:
                data=json.loads(r['datastring'])
                workerID = data["workerId"]
                trials_data = get_trials_data(data)
                session = get_session(trials_data)
                trials.append(len(trials_data))
                workerIDs.append(workerID)
                hits.append(data["hitId"])
                sessions.append(session)
                if len(trials_data) > 0:
                    phase.append(trials_data[-1]["phase"])
                else:
                    phase.append("X")

        idx=argsort(trials)


	try:
		return render_template('list.html', participants=workerIDs,hits=hits,trials=trials,sessions=sessions,phase=phase,sort_idx=idx)
	except TemplateNotFound:
		abort(404)

#----------------------------------------------
# example computing bonus
#----------------------------------------------
@custom_code.route('/compute_bonus', methods=['GET'])
def compute_bonus():
    # check that user provided the correct keys
    # errors will not be that gracefull here if being
    # accessed by the Javascrip client
    if not request.args.has_key('uniqueId'):
        raise ExperimentError('improper_inputs')  # i don't like returning HTML to JSON requests...  maybe should change this
    uniqueId = request.args['uniqueId']

    try:
        print "looking for user: ", uniqueId
        # lookup user in database
        user = Participant.query.\
               filter(Participant.uniqueid == uniqueId).\
               one()
        user_data = loads(user.datastring) # load datastring from JSON
        bonus = 0
        print "found it. computing his bonuses."

        data = user_data['data']
        for report in data: # for line in data file
            trial = report['trialdata']
            if trial["phase"]==TASK:
                bonus=trial['total_reward']

        bonus = round(bonus,2)
        print "bonus: ",bonus
        user.bonus = bonus
        db_session.add(user)
        db_session.commit()
        print "commited to db"
        resp = {"bonusComputed": "success"}
        return jsonify(**resp)
    except:
        abort(404)  # again, bad to display HTML, but...

#----------------------------------------------
# get a session of stimuli
#----------------------------------------------

@custom_code.route('/stuff', methods=['GET'])
def stuff():
    return jsonify(results=list(all_trials[0]))

@custom_code.route('/get_stims', methods=['GET'])
def get_stims():

    # trialset = load_from_db(params)
    # return trialset
    # if not request.args.has_key('n_trials'):
    #     abort(400)

    params = {}
    params["n_trials"]  = int(request.args['n_trials'])
    params["stims"]  = request.args['stims']
    params["delays"]  = request.args['delays']

    params["stims"]  = map(int,params["stims"].split(","))
    params["delays"] = map(int,params["delays"].split(","))


    try:
        trialset = load_from_db(params)
        return jsonify(results=trialset)
    except:
        abort(404)

def gen_trial_idx(max_t,n):
    assert max_t > n
    trial_idx = []
    i=random.randint(0,max_t-1)

    for _ in range(n):
        while i in trial_idx:
            i=random.randint(0,max_t-1)
        trial_idx.append(i)

    return trial_idx

def load_from_db(params):
    trialset = []
    if 0 in params["delays"]:
        params["delays"].pop(params["delays"].index(0))

    for show in [0,1]:
        for delay in params["delays"]:
            for stim in params["stims"]:
                trials = all_trials[stim-1]
                trial_idx = gen_trial_idx(len(trials),params["n_trials"])
                # need to add delay here
                trialset += add_cond(trials[trial_idx].tolist(),["delay","show"],[delay,show])

    # for stim in params["stims"]:
    #     trials = all_trials[stim-1]
    #     trial_idx = gen_trial_idx(len(trials),params["n_trials"])
    #     # need to add delay here
    #     trialset += add_cond(trials[trial_idx].tolist(),["delay","show"],[0,0])

    return trialset

def add_cond(trial_list,conds_s,cond):
    for t in trial_list:
        for s in range(len(t)):
            for i,cond_s in enumerate(conds_s):
                t[s][cond_s] = cond[i]

    return trial_list

def get_trials_data(data):
    idx = find([not d['trialdata']['phase'] for d in data["data"]])
    trialdata = [data["data"][i]["trialdata"] for i in idx]
    trialdata = [d["trialdata"] for d in data["data"]]

    return trialdata

params = {}
params["delays"]=[0,3]
params["n_trials"]  = 10
params["stims"] = [1,2,3,4]
