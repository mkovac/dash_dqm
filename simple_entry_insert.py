
import argparse
import getpass
import msggen
import json
from logdb import * 
import oracledb
import sqlalchemy
from sqlalchemy import create_engine
import datetime

oracledb.init_oracle_client()

parser = argparse.ArgumentParser('Dash Display Test for Rundbv2')
parser.add_argument('-r', '--run', type=int, help='Run number to use as key')



dbEngine = None
session = None
password = getpass.getpass()


args = parser.parse_args() 

try:

    connectS = "(DESCRIPTION = \
    (ADDRESS=(PROTOCOL = TCP)(HOST = int2r-s.cern.ch)(PORT = 10121)) \
    (CONNECT_DATA= (SERVICE_NAME = int2r_lb.cern.ch) \
    (SERVER = DEDICATED)) \
    )"
    print(f'Trying to connect to oracle using {connectS}')

    dbEngine = create_engine(f"oracle+oracledb://",
                             connect_args = { "user":"ecal_p2ug_conf_dev",
                                              "password":password,
                                              "dsn":connectS
                                             })
    session = Session(dbEngine)

except Exception as e:
    print(f'Error opening dB {e}')
    exit()








RunInfos = session.execute(select(RunInfo).where(RunInfo.run_number == args.run)).scalars().all()
tests = session.execute(select(Test)).scalars().all()
testmap = {}
for test in tests:
    testmap[test.name] = test

    
if RunInfos:
    # use first RI and first part of random msg  (for now)
    headRI = RunInfos[0]
    msg = msggen.random_bcp_message(args.run)
    entry = Entry()
    entry.run_number = args.run
    entry.location = headRI.location
    entry.test_id = testmap[msg.test_id].id
    entry.func_name = msg.results[0]['func_name']
    entry.result = json.dumps(msg.results[0]['results'])
    entry.test_timestamp = msg.results[0]['timestamp']
    session.add(entry)
    session.commit()

else:
    print(f'Could not find run {args.run}')


    
    
                           
