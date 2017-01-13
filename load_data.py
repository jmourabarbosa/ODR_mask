from sqlalchemy import create_engine, MetaData, Table
import json
import pandas as pd
from matplotlib.mlab import find
from numpy import *
from matplotlib.mlab import *
from circ_stats import *
from scipy.io import savemat
import sys
import os
import scikits.bootstrap as bootstrap
import statsmodels.api as sm



# db_url = "sqlite:///"+sys.argv[1]

# table_name = 'swaps'
# data_column_name = 'datastring'
# # boilerplace sqlalchemy setup
# engine = create_engine(db_url)
# metadata = MetaData()
# metadata.bind = engine
# table = Table(table_name, metadata, autoload=True)
# # make a query and loop through
# s = table.select()
# rows = s.execute()
# rs = []
# ds = []


dbs = amap(lambda x: x.split(".db"),os.listdir(sys.argv[1]))
dbs = dbs[amap(len,dbs)>1]

Rows = []
for db in dbs:
	db_url = "sqlite:///"+sys.argv[1]+db[0]+".db"
	table_name = 'swaps'
	data_column_name = 'datastring'
	# boilerplace sqlalchemy setup
	engine = create_engine(db_url)
	metadata = MetaData()
	metadata.bind = engine
	table = Table(table_name, metadata, autoload=True)
	# make a query and loop through
	s = table.select()
	rows = s.execute()
	Rows.append(rows)

def to_pi(angles):
	angles = array(angles)
	idx = angles>pi
	angles[idx] = angles[idx]-2*pi
	return angles

# filter subjects with no real experiment
def get_trials_data(data):
	idx = find([not d['trialdata']['phase'] for d in data["data"]])
	trialdata = [data["data"][i]["trialdata"] for i in idx]
	return trialdata

def filter_data(data):
	trials = []
	for d in data:
		trial = {}
		trial["load"] = d["load"]

		assert d["load"] == len(json.loads(d["trial"]))
		assert d["show"] == json.loads(d["session"])["show"]
		trial["delay"] = d["delay"]
		trial["show"] = d["show"]
		trial["report_color"] = d["report_color"]
		trial["rt"] = d["rt"]

		stims = json.loads(d["trial"])
		stims = json.loads(d["session"])["trial"]
		NT = []
		for i,s in enumerate(stims):
			if s["correct"]:
				trial["T_color"] = s["color"]
				trial["T_pos"] = s["pos_angle"]
			else:
				NT.append([s["color"],s["pos_angle"]])

		for i,[color,pos] in enumerate(NT):
			trial["NT_color"+str(i)] = color
			trial["NT_pos"+str(i)] = pos

		trials.append(trial)
	return trials


all_trials  = {}
for rows in Rows:
	for r in rows:
		if r["datastring"]:
			data=json.loads(r['datastring'])
			workerID = data["workerId"]
			trials_data = get_trials_data(data)
			if len(trials_data) > 90:
				all_trials[workerID] = filter_data(trials_data)



good_workers = all_trials.keys()


X=[]
T_c=[]
T_p = []
NT_c = []
NT_p = []
D=[]
C=[]
loads = []
RT=[]

for wid in good_workers:

	x=[]
	t_c=[]
	t_p=[]
	nt_c=[]
	nt_p=[]	
	d=[]
	c=[]
	rt=[]

	for trial in all_trials[wid]:
		load = trial["load"]
		loads.append(load)
		x.append(trial["report_color"])
		t_c.append(trial["T_color"])
		t_p.append(trial["T_pos"])
		d.append(trial["delay"])
		c.append(trial["show"])
		rt.append(trial["rt"])


		nt_c1=[]
		nt_p1=[]
		for nt in range(load-1):
			nt_c1.append(trial["NT_color"+str(nt)])
			nt_p1.append(trial["NT_pos"+str(nt)])
		nt_c.append(nt_c1)
		nt_p.append(nt_p1)

	X.append(x)
	T_c.append(t_c)
	T_p.append(t_p)
	NT_c.append(nt_c)
	NT_p.append(nt_p)
	D.append(d)
	C.append(c)
	RT.append(rt)

rt = concatenate(RT)
x=concatenate(X)
t_c = concatenate(T_c)
t_p = concatenate(T_p)
nt_c = concatenate(NT_c)
nt_p = concatenate(NT_p)
c=concatenate(C)
d=concatenate(D)
c= (c==1)
d=(d==0)

RT_show=[]
RT_hide=[]

X_show =[]
T_show =[]
NT_show =[]

X_hide =[]
T_hide =[]
NT_hide =[]

# colapsing all loads
# nt_idx = amap(len,nt_c) >0
# for i,nt in enumerate(nt_c[nt_idx]):
# 	dist_to_nt = abs(circdist(x[nt_idx][i],nt))
# 	close = argsort(dist_to_nt)[0]
# 	X_show.append(x[nt_idx][i])
# 	T_show.append(t_c[nt_idx][i])
# 	NT_show.append(nt[close])

# c = c[nt_idx]
# X_show = array(X_show)
# T_show = array(T_show)
# NT_show = array(NT_show)

# X_hide = X_show[c==0]
# T_hide = T_show[c==0]
# NT_hide =NT_show[c==0]


# X_show = X_show[c==1]
# T_show = T_show[c==1]
# NT_show =NT_show[c==1]

clean_idx = (rt/1000. < 5) & (rt/1000. > 1)

for load in unique(loads):
	if load == 1:
		continue 
	idx = load == loads
	idx = idx & clean_idx
	X_show+=[x[idx & c & d]]
	X_hide+=[x[idx & ~c & d]]
	T_show+=[amap(to_pi,t_c[idx & c & d])]
	T_hide+=[amap(to_pi,t_c[idx & ~c & d])]
	NT_show+=[amap(to_pi,nt_c[idx & c & d])]
	NT_hide+=[amap(to_pi,nt_c[idx & ~c & d])]
	RT_show+=[rt[idx & c & d]]
	RT_hide+=[rt[idx & ~c & d]]




X_hide=array(X_hide)
T_hide =array(T_hide)
NT_hide =array(NT_hide)
hide_d = {"X": X_hide, "T": T_hide, "NT": NT_hide}

X_show = array(X_show)
T_show = array(T_show)
NT_show = array(NT_show)
show_d = {"X": X_show, "T": T_show, "NT": NT_show}

savemat("show_d.mat",show_d)
savemat("hide_d.mat",hide_d)

figure()
title("mean error")
mean_err = array([bootstrap.ci(abs(circdist(X_show[i],T_show[i])),circmean) for i in range(len(X_show))])
plot(unique(loads),ones(len(unique(loads)))*mean(mean_err[0]),"b--",label="show")
plot(unique(loads),mean(mean_err,1),"b")
plot(unique(loads),mean(mean_err,1),"bo",ms=5)

fill_between(unique(loads),mean_err[:,0],mean_err[:,1],alpha=0.1,color="blue")

mean_err = array([bootstrap.ci(abs(circdist(X_hide[i],T_hide[i])),circmean) for i in range(len(X_hide))])
plot(unique(loads),ones(len(unique(loads)))*mean(mean_err[0]),"r--",label="hide")
plot(unique(loads),mean(mean_err,1),"r")
plot(unique(loads),mean(mean_err,1),"ro",ms=5)

fill_between(unique(loads),mean_err[:,0],mean_err[:,1],alpha=0.1,color="red")
xlabel("number of stimuli")
ylabel("abs error (rad)")
legend()


figure()
title("mean RT")

# for i in range(len(RT_show)): 
# 	RT_show[i]=RT_show[i][RT_show[i]<3*std(RT_show[i])]
# 	RT_show[i] = array(RT_show[i])/1000.

# for i in range(len(RT_hide)): 
# 	RT_hide[i]=RT_hide[i][RT_hide[i]<3*std(RT_hide[i])]
# 	RT_hide[i] = array(RT_hide[i])/1000.

load_show = concatenate([ones(len(RT_show[i]))*(i+1) for i in range(len(RT_show))])
load_show = sm.add_constant(load_show)
s=sm.OLS(concatenate(RT_show),load_show)
r=s.fit()
b_show,l_show=r.params
plot(unique(loads), l_show*unique(loads)+ b_show, "b-",lw=5)


load_hide = concatenate([ones(len(RT_hide[i]))*(i+1) for i in range(len(RT_hide))])
load_hide = sm.add_constant(load_hide)
s=sm.OLS(concatenate(RT_hide),load_hide)
r=s.fit()
b_hide,l_hide=r.params
plot(unique(loads), l_hide*unique(loads)+ b_hide, "r-",lw=5)

# plot(unique(loads),amap(mean,RT_show),"bo",label="show")
# plot(unique(loads),amap(mean,RT_hide),"ro",label="hide")

plot(unique(loads),amap(mean,RT_show),"bo",label="show")
plot(unique(loads),amap(mean,RT_hide),"ro",label="hide")

# l = unique(loads)
# for i in range(len(RT_show)):
# 	[plot(l[i],r,"b.",alpha=0.1) for r in RT_show[i]]
# 	[plot(l[i],r,"r.",alpha=0.1) for r in RT_hide[i]]


def stderr(data):
	return mean(data)/sqrt(len(data))

errorbar(unique(loads),amap(mean,RT_show),amap(stderr,RT_show), fmt='o',color="blue")
errorbar(unique(loads),amap(mean,RT_hide),amap(stderr,RT_hide), fmt='o',color="red")

xlabel("number of stimuli")
ylabel("reaction time (msec)")
xlim(1,7)

legend()

