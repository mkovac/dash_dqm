import json
import random
import datetime 

    

def gen_random_time():
    today = datetime.datetime.today()
    rndHour = random.randint(0,23)
    rndMin = random.randint(0,59)
    rndSec = random.randint(0,59)
    delta = datetime.timedelta(hours = rndHour,
                               minutes = rndMin,
                               seconds = rndSec)
    return today+delta

def gen_configureslpgbt():
    d = {}
    d['func_name'] = 'configureslpgbt'
    d['result'] = ''
    d['timestamp'] = gen_random_time().timestamp()

    return d

def gen_configureslpgbts():
    d = {}
    d['func_name'] = 'configureslpgbts'
    d['result'] = {
	"1": {
	    "lpgbts_tclink_status": "TCLink status: 15,14,14,14,",
	    "slave1_chip_id": "acac3c3c",
	    "slave1_status": 19,
	    "slave2_chip_id": "842df0a6",
	    "slave2_status": 19,
	"slave3_chip_id": "6c2d30e7",
	"slave3_status": 19
        }
        }
    d['timestamp'] = gen_random_time().timestamp()
    return d
    
def gen_resetvfes():
    d = {}
    d['func_name'] = 'resetvfes'
    d['timestamp'] = gen_random_time().timestamp()
    d['result'] = {'1':'success'}

    return d

def gen_getbitslips():
    d = {}
    d['func_name'] = 'getbitslips'
    d['timestamp'] = gen_random_time().timestamp()
    d['result'] = {"1": [
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0,
		    0
		]
                   }
    return d


def gen_optimizevrefs():
    d = {}
    d['func_name'] = 'optimizevrefs'
    d['timestamp'] = gen_random_time().timestamp()
    d['result'] = { '1': [ 		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9,
		    9
                    ]
                    }
    return d

def gen_calibrateadcs():
    d = {} 
    d['func_name'] = 'calibrateadcs'
    d['timestamp'] = gen_random_time().timestamp()
    d['result'] = { '1':'success' }
    return d

def gen_optimize_ped_rogue():
    d = {} 
    d['func_name'] = 'optimize_ped_rogue'
    d['timestamp'] = gen_random_time().timestamp()
    d['result'] = [ 'DONE' ]
    return d

def gen_launchprbstest():
    d = {} 
    d['func_name'] = 'launchprbstest'
    d['timestamp'] = gen_random_time().timestamp()
    d['result'] = {
        "towers": {
	    "1": {
		"links": {
		    "0": {
			"endTime": 1776952748589701801,
			"errors": 0
		    },
		    "1": {
			"endTime": 1776952748790347131,
			"errors": 0
		    },
		    "2": {
			"endTime": 1776952748990983548,
			"errors": 0
		    },
		    "3": {
			"endTime": 1776952749191657039,
			"errors": 0
		    }
		}
        }
        }
        }
    return d




func_names = {
    'configuremlpgbt':gen_configureslpgbt,
    'configureslpgbts':gen_configureslpgbts,
    'resetvfes':gen_resetvfes,
    'getbitslips':gen_getbitslips,
    'optimizevrefs':gen_optimizevrefs,
    'calibrateadcs':gen_calibrateadcs,
    'optimize_ped_rogue':gen_optimize_ped_rogue,
    'launchprbstest':gen_launchprbstest
    }

test_ids = {
    'configuremlpgbt':['configuremlpgbt'],
    'configureslpgbts':['configureslpgbts'],
    'resetvfes': ['resetvfes'],
    'aligndtus':['getbitslips'],
    'optimizevrefs':['optimizevrefs'],
    'optimizepedestals':['calibrateadcs', 'optimize_ped_rogue'],
    'launchprbstest':['launchprbstest']
    }





    

class result:
    def __init__(self):
        self.func_name = ""
        self.result = {}
        self.timestamp = -1



        
def random_result(kind):
    r = result()
    if kind not in func_names.keys():
        print(f'error! Bad kind for random result {kind}')
        return r
    
    r.func_name = kind
    r.timestamp = gen_random_time().timestamp()
    r.result = func_names[r.func_name]()
    return r
        

class bcp_message:
    def __init__(self):
        self.location = ""
        self.msg_id = ""
        self.results = []
        self.run_number = -1
        self.sm_id = -1
        self.test_id = ""
        self.timestamp = gen_random_time()
        self.towers = []
        self.tgid = ""

    def json(self):
        d = {}
        d['location'] = self.location
        d['msg_id'] = self.msg_id
        d['results'] = self.results
        d['run_number'] = self.run_number
        d['test_id'] = self.test_id
        d['sm_id'] = self.sm_id
        d['tgid'] = self.tgid
        d['timestamp'] = self.timestamp.timestamp()
        d['towers'] = self.towers
        return json.dumps(d)
        

def random_bcp_message(run_number=1, test_group='test_tt'):

    msg = bcp_message()
    msg.location = 'P5'
    msg.msg_id = 'BCP3'
    msg.run_number = run_number
    msg.sm_id = 1
    msg.test_id = random.choice(list(test_ids.keys()))
    msg.results = []
    msg.tgid = test_group
    for test in test_ids[msg.test_id]: 
        msg.results.append(func_names[test]())
    
    msg.timestamp = gen_random_time()
    
    msg.towers = []
    towers = list(range(0,40))
    
    for i in range(0,3):
        twr = random.choice(towers)
        msg.towers.append(twr)
        towers.remove(twr)

    return msg
        
        

def process_json_msg(msg):
    keys = {'location', 'msg_id', 'run_number', 'sm_id', 'test_id', 'results', 'tgid', 'towers', 'timestamp' }
    diff = keys.difference(set(msg.keys()))
    if len(diff) > 0:
        print(f'Msg either has or is missing extra slots {msg}')
        return None
    
    
    
