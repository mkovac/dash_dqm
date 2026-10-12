from logdb import *

import argparse
import pathlib


parser = argparse.ArgumentParser('Log DB Table Generator')
parser.add_argument('--db', type=str, default='sqlite', choices=['sqlite', 'oracle'], help='Oracle or SQLite')
parser.add_argument('-f', '--file', type=str, default='log.db', help='File for use w/SQLite')
parser.add_argument('-u', '--user', type=str, default='', help='User for OracleDB')
parser.add_argument('-p', '--password', type=str, default='', help='Password for OracleDB')
parser.add_argument('-c', '--host', type=str, default='localhost', help='Host for OracleDB')




def populate_database(connectionType, fname, connargs):

    dbEngine = None 
    session = None 
    connStr = '' 
    if connectionType == 'sqlite':
        path = pathlib.Path(fname)
        if path.exists():
            print(f"Error {fname} already exists")
            exit()

        connStr = f'sqlite:////{path.absolute()}'
        dbEngine = create_engine(connStr, echo=True, connect_args={'autocommit':True})
    elif connectionType == 'oracle':
        connStr = f'oracle+oracledb://{connargs["user"]}:{connargs["password"]}@{connargs["host"]}'
        dbEngine = create_engine(connStr)
        

    session = Session(dbEngine)
    
    #dbPath = 'junk.db'
    #liteEngine = create_engine('sqlite:///' + str(dbPath), echo=False, connect_args={'autocommit':True})
    
    # Create tables
    Base.metadata.create_all(dbEngine)
    # Create SuperModules
    supermodules = []
    for i in range(3):
        sm = Supermodule(id=i+1,construction_id=i+1)
        supermodules.append(sm)
        session.add(sm)
        
    # Create Tests
    test_names = ["configuremlpgbt", "configureslpgbts","resetvfes","aligndtus","optimizevrefs", "optimizepedestals","launchprbstest"]
    tests = []
    for i, name in enumerate(test_names):
        test = Test(id=i+1, name=name, description=f"Description for {name}")
        tests.append(test)
        session.add(test)
        
    # Create Towers
    towers = []
    for i in range(70):
        tower = Tower(id_tower=i, id_supermodule=1, tower_in_sm=1, eta_sm=0, phi_sm=0)
        towermap = TowerMapping()
        towermap.tower_num_sm = i
        towermap.tower_num_bcp = 1
        towermap.bcp_num = 1

        

        #tower = Tower(tid=i+1, notes=f"Notes for tower {i+1}")
        towers.append(tower)
        session.add(tower)
        session.add(towermap)

        
    session.commit()
    print("Database populated with random data")

if __name__ == '__main__':
    args = parser.parse_args()
    connType = args.db
    connArgs = {'user':"", 'password':"", 'host':""}
    fname = args.file
    if (args.db == 'sqlite'):
        print('Using SQLite')
    elif (args.db == 'oracle'):
        print('Using Oracle')
        connArgs['user'] = args.user
        connArgs['password'] = args.password
        connArgs['host'] = args.host


    
    populate_database(connType,fname,connArgs)
