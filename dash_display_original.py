from logdb import *

from dash import Dash, html, dcc
import dash_ag_grid as dag
import datetime

import pathlib
import argparse

import sqlalchemy
from sqlalchemy import create_engine
import oracledb
import getpass
oracledb.init_oracle_client()

parser = argparse.ArgumentParser('Dash Display Test for Rundbv2')
parser.add_argument('-f', '--db', default='junk.db', type=str, help='SQLite Database file')
parser.add_argument('-o', '--oracle', action='store_true', help='Connect to Oracle Database')

args = parser.parse_args() 



dbEngine = None
session = None
password = None

# Note to self, add option to pull from an environmental variable to reduce the amount
# of entering the pw
if (args.oracle):
    print('Getting pass')
    password = getpass.getpass()
try:


    if args.oracle:
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

    else:
        path = pathlib.Path(args.db)
        if not path.exists():
            print(f'Error database {path} does not exist!')
            exit()
        
        connStr = f'sqlite:////{path.absolute()}'
        print(f'Opening {connStr}')
        dbEngine = create_engine(connStr, echo=True, connect_args={'autocommit':True})
        
        session = Session(dbEngine)
        session.execute(sqlalchemy.text("PRAGMA foreign_keys=ON"))
    
except Exception as e:
    print(f'Error opening dB {e}')
    exit()


Runs = session.execute(select(Entry)).scalars().all()
Tests = session.execute(select(Test)).scalars().all()
RunInfos = session.execute(select(RunInfo)).scalars().all()


columns = [
    {'headerName':'Run #', 'valueGetter':{'function':'params.node.id'}},
    {'field':'entry_id'},
    {'field':'test_name'},
    {'field':'func_name'},
    {'field':'results'},
    {'field':'timestamp'}
    ]

runColumns = [
    {'headerName':'Run #', 'valueGetter':{'function':'params.node.id'}},
    {'field':'supermodule'},
    {'field':'starttime'},
    {'field':'endtime'},
    {'field':'entries'}
    ]


runInfolst = []

for r in RunInfos:
    d = {}
    d['id'] = r.run_number
    d['supermodule'] = r.sm
    d['starttime'] = r.starttime
    d['endtime'] = r.endtime
    d['entries'] = len(r.entries)
    runInfolst.append(d)
    
runlst = []

for r in Runs:
    d = {}
    d['id'] = r.run_number
    d['entry_id']=  r.entry_id
    d['test_name'] = r.test.name
    d['func_name'] = r.func_name
    d['results'] = r.result
    d['timestamp'] = datetime.datetime.fromtimestamp(r.test_timestamp)
    runlst.append(d)


    
dashApp = Dash()

testEntryGrid = html.Div([
    html.H6('Test Entries'),
    dag.AgGrid(
        rowData = runlst,
        columnDefs=columns,
        getRowId='params.data.id'),
    html.Br()
    ])

testRIGrid = html.Div([
    html.H6('Run Infos'),
    dag.AgGrid(
        rowData = runInfolst,
        columnDefs = runColumns,
        getRowId = 'params.data.id'),
    html.Br()
    ])

dashApp.layout = [ testEntryGrid, testRIGrid]

dashApp.run(debug=True,use_reloader=False)

