/*
 * Requires:
 *     psiturk.js
 *     utils.js
 */

// Initalize psiturk object
var psiTurk = new PsiTurk(uniqueId, adServerLoc, mode);

var mycondition = condition;  // these two variables are passed by the psiturk server process
var mycounterbalance = counterbalance;  // they tell you which condition you have been assigned to
// they are not used in the stroop code but may be useful to you

// All pages to be loaded
var pages = [
	"instructions/instruct-1.html",
	"instructions/instruct-2.html",
	"instructions/instruct-3.html",
	// "instructions/instruct-4.html",
	"instructions/instruct-5.html",
	"instructions/instruct-6.html",
	// "instructions/instruct-7.html",
	"instructions/instruct-8.html",
	"instructions/instruct-ready.html",
	"color_blind.html",

	"repeat_task.html",
	"before_task.html",
	"stage.html",
	"thanks.html",
	"press_space.html",
	"postquestionnaire.html",
	"error.html",
];

psiTurk.preloadPages(pages);

var instructionPages = [ // add as a list as many pages as you like
	"instructions/instruct-1.html",
	"instructions/instruct-2.html",
	"instructions/instruct-3.html",
	"instructions/instruct-5.html",
	"instructions/instruct-6.html",
	"instructions/instruct-8.html",
	"instructions/instruct-ready.html"
];

var before_task = [
	"before_task.html"
];

var repeat_task = [
	"repeat_task.html"
];



var images = [
			"static/images/wheel0.png",
			"static/images/wheel90.png",
			"static/images/wheel180.png",
			"static/images/wheel270.png",
			];


psiTurk.preloadImages(images);

var session = {}

// Wheel parameters
var wheel_offset = [deg2rad(0),deg2rad(90),deg2rad(180),deg2rad(270)];
var wheel_offset = d3.range(0,2*math.pi,0.1);

SCR_X = 600
SCR_Y = 600
WHEEL_X = 600
WHEEL_Y = 600
CENTER = [SCR_X/2,SCR_X/2]
STIM_SIZE=20
RADIUS = WHEEL_Y/3.2

// Task stage codes
FIX=0
PRES = 1
DELAY = 2
REPORT = 3
FINISH = 4

// Task durations
FIX_DUR = 500
PRES_DUR = 500
DELAY_DUR = 0//3000
FEED_DUR = 500
FLIP_DUR = 50
TOTAL_DUR = FIX_DUR + PRES_DUR + DELAY_DUR


// Task phase codes
TEST = 1
TASK = 0

CORRECT = 0
CATCH=1

SPACE = 32
DOWN=1
UP=0
MAX_CATCH=2
CATCH_INTERVAL=500
CATCH_TIMEOUT=1000
CORRECT_THR=0.5

WHITE=0
BLACK=1
FIX_SIZE = 20

MAX_RWD = 10

N_SEGS = 90


/************************
* SWAP ERROR EXPERIMENT *
*************************/

var StroopExperiment = function(trials) {

	var next = function() {
		if (session["trials"].length<session["trial_number"]+1) {
			finish();
		}
		else {
			session["trial"] = session["trials"][session["trial_number"]];
			session["delay"] = session["trial"][0]["delay"]*1000
			session["state"] = FIX;
			session["show"] = session["trial"][0]["show"]
			session["n_stims"] = session["trial"].length
			screen = start_screen();
			draw_fix(screen,"white");
			$("#fixation").mouseover(show_trial)
			psiTurk.saveData()
		}
	};
	
	var response_handler = function(e) {
		if (!session["listening"]) return;

		session["listening"] = 0;

		offset = $(this).offset()
		report_x = e.clientX
		report_y = e.clientY

		report_x = e.pageX - offset.left;
    	report_y = e.pageY - offset.top;

    	if (!report_x & !report_y){
    		report_x = report_y = 1;
    	}


		report_angle = pos2angle([report_x,report_y],CENTER);

		report_pos = angle2pos(report_angle,250,CENTER);
		report_pos = [report_x,report_y];
		report_on_screen = [report_x,report_y]

		rt = new Date().getTime() - session["wheel_on"];

		// avoid saving all trials everytime
		// restore below
		trials = session["trials"]
		session["trials"] = 0


		psiTurk.recordTrialData({
									'trial_number': session["trial_number"],
									'rt':rt,
									'phase':session["phase"],
									'report_pos': report_pos,
									'report_pos': report_angle,
									'trial': JSON.stringify(trial),
									'acc_rwd': session["acc_rwd"],
									'total_reward': math.round(session["trial_number"]*params["hit_reward"],2),
									'session': JSON.stringify(session)
                               });

		// restore here
		session["trials"] = trials

		// reset session variables
		session_init()
		session["trial_number"]++;
		nanobar()
		feedback(report_pos)
		setTimeout(function () {next()},FEED_DUR)
	};


	




	var show_trial = function () {
		trial=session["trial"];
		state = session["state"];

		switch (state){


			// Fixation
			case FIX:
				screen = start_screen();
				draw_fix(screen,"black");
				session["state"] = PRES;
				setTimeout(function () {show_trial()},FIX_DUR)
				break;

			// Presentation
			case PRES:
				screen = start_screen();
				draw_fix(screen,"black")
				draw_stims(screen);

				session["state"] = DELAY;
				setTimeout(function () {show_trial()},PRES_DUR)
				break;

			// Delay 
			case DELAY:
				hide_stimulus()
				session["state"] = REPORT;
				setTimeout(function () {show_trial()},session["delay"])
				break;

			// Report
			case REPORT:
				session["state"] = FINISH
				session["wheel_on"] = new Date().getTime();
				session["listening"] = true
				draw_fix(screen,"white");
				$("#all_stims").click(response_handler);
				break;
		}


	};

	var abort = function(){

		value = math.round(session["trial_number"]*params["hit_reward"],2)

		answer = confirm("Do you want to leave with with a bonus of $"+value+"?");

		if (answer) {
			session["abort"]=true
			psiTurk.showPage('thanks.html'); 
			currentview = new Questionnaire();
		}
	}

	var finish = function() {
	switch (session["phase"]) {

		case TASK:
			psiTurk.showPage('repeat_task.html');

			$("#repeat").click(function () { 
				// MAKE SURE n_trials is not reset
				gen_trials2(params,exp_callback)
			});

			$("#finish").click(function () {
				psiTurk.showPage('thanks.html');
				currentview = new Questionnaire();});
			break;

		case TEST:
			psiTurk.showPage('before_task.html');

			$("#repeat").click(start_test);
			$("#begin").click(function () {
				session['phase'] = TASK; 
				session["session"]=0;
				session["trial_number"]=0;
		 		params = default_params(TASK);
		 		gen_trials2(params,exp_callback);
		 	});
    		break;
		} 

	};

	trials = _.shuffle(trials)


	// Initialize experiment variables
	session['trials'] = stretch_stims(trials);
	session['trial_number'] = 0;
	session["total_trials"] = trials.length
	session['start_time'] = Date.now()
	session["bar"] = undefined
	session["abort"] = false 
	session["sessions"]+=1
	session_init();

	// Load the stage.html snippet into the body of the page
	psiTurk.showPage('stage.html');
	session["bar"] = nanobar()

	$("#abort").click(function () { abort()});

	psiTurk.recordTrialData({
							'phase': 'all trials',
							'trials': JSON.stringify(trials)
                       });

	// Start the experiment
	next();
};

exp_callback = function(trials,params) { session["params"] = params;currentview = new StroopExperiment(trials) }

var start_test = function(){

	params = default_params(TEST);
	session['phase'] = TEST
    psiTurk.doInstructions(
    	instructionPages, 
    	function () { gen_trials2(params,exp_callback)}
    );
}

// Task object to keep track of the current phase
var currentview;

/*******************
 * Run Task
 ******************/
$(window).load( function(){

	start_test();
	
});
