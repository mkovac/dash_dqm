import getpass
import sys
from datetime import datetime, timezone

import oracledb
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from logdb import Entry, Test

# Connect to the INT2R database
oracledb.init_oracle_client()
dsn = ("(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=int2r-s.cern.ch)(PORT=10121))"
       "(CONNECT_DATA=(SERVICE_NAME=int2r_lb.cern.ch)(SERVER=DEDICATED)))")
engine = create_engine("oracle+oracledb://", connect_args={
    "user": "ecal_p2ug_conf_dev", "password": getpass.getpass(), "dsn": dsn})

# All entries with their test name, newest first
query = (select(Entry, Test.name)
         .join(Test, Entry.test_id == Test.id)
         .order_by(Entry.entry_id.desc())
         .limit(50))

# Optional: filter by run number given on the command line
if len(sys.argv) > 1:
    query = query.where(Entry.run_number == int(sys.argv[1]))

fmt = "{:>8}  {:>5}  {:<18} {:<18} {:<20} {}"

with Session(engine) as s:
    total = s.scalar(select(func.count()).select_from(Entry))
    print(f"ecal_logger_entries: {total} rows in total\n")

    print(fmt.format("entry_id", "run", "test", "func_name", "time (UTC)", "result"))
    for e, test_name in s.execute(query):
        t = datetime.fromtimestamp(e.test_timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(fmt.format(e.entry_id, e.run_number, test_name, e.func_name, t, e.result[:1000]))