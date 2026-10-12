# ECAL DQM logger and dashboard

Test setup for collecting BCP log messages over MQTT, storing them in Oracle, and displaying them in a web dashboard.

The base code is taken from the `cleanup` branch of [tanderso/dash_dqm](https://gitlab.cern.ch/tanderso/dash_dqm/-/tree/cleanup?ref_type=heads) on CERN GitLab.

```
publishers --MQTT--> NanoMQ broker --> mqttClientOracle.py --> Oracle (INT2R) --> dash_display.py
```

| Component | Role |
|---|---|
| NanoMQ | Off-the-shelf MQTT broker. Forwards messages; not modified by this project. |
| `mqttClientOracle.py` | Subscribes to `runs/#` and `control/#`, queues incoming messages. |
| `logmsgHandler.py` | Validates messages and writes them to the database (worker thread). |
| `message_handlers.py` | Per-function processing of each result, selected by `func_name`. |
| `logdb.py` | SQLAlchemy table definitions. |
| `dash_display.py` | Dash web app that reads from the database. |
| `show_entries.py` | Read-only script that prints stored entries. |

## 1. Environment

On lxplus (or another AlmaLinux 9 machine with CVMFS):

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh
```

This provides the compiler, CMake, Ninja and Python.

## 2. Build the NanoMQ broker

```bash
git clone https://github.com/nanomq/nanomq
cd nanomq
git submodule update --init --recursive --depth 1
mkdir build && cd build
cmake -G Ninja ..
ninja
```

The full build is about 700 MB with external modules; the broker and library alone are about 120 MB.

## 3. Run the broker

```bash
cd nanomq/build/nanomq
nohup ./nanomq start > nanomq.log 2>&1 &
```

This runs it in the background and writes its output to `nanomq.log`. It listens on port 1883. A "config file not found" error in the log is harmless; the defaults are used. To use a config file:

```bash
nohup ./nanomq start --conf ../../etc/nanomq.conf > nanomq.log 2>&1 &
```

Useful commands:

```bash
pgrep -a nanomq            # is it running?
ss -ltn | grep 1883        # is it listening?
tail -f nanomq.log         # follow its output
pkill nanomq               # stop it
```

On lxplus, each login may land on a different node. Note the `hostname` where the broker runs.

## 4. Python environment

Create once:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install Flask oracledb paho-mqtt SQLAlchemy dash dash_ag_grid
```

In every new shell:

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh
source venv/bin/activate
```

If you get `ModuleNotFoundError`, the venv is not active or a package is missing; install it with `python -m pip install <name>`.

## 5. Run the logger

```bash
python mqttClientOracle.py                 # broker on localhost
python mqttClientOracle.py --host <host>   # broker elsewhere
```

It prompts for the Oracle password of account `ecal_p2ug_conf_dev` (ask the project maintainers; never commit it). A healthy startup ends with:

```
INFO:__main__:Ready
INFO:__main__:Subscribing to runs/# and control/#
INFO:__main__:Broker granted QoS 0
INFO:__main__:Broker granted QoS 0
```

To run it in the background after entering the password: press `Ctrl-Z`, then type `bg`. Use `jobs`, `fg` and `kill %1` to manage it.

Sending a message containing `stop` to a `control/...` topic shuts the logger down.

## 6. Run the dashboard

```bash
python dash_display.py -o        # -o reads from Oracle
```

It serves on `http://127.0.0.1:8050/` of the remote machine. To view it from your laptop:

```bash
ssh -L 8050:localhost:8050 <user>@<exact-lxplus-node>.cern.ch
```

then open `http://localhost:8050`.

## 7. Inspect the database

```bash
python show_entries.py           # all entries, newest first
python show_entries.py 344       # only run 344
python show_entries.py > entries.txt
```

## Message format

Messages on `runs/...` must be JSON:

```json
{
  "location": "...", "msg_id": "...", "run_number": 344,
  "sm_id": "...", "test_id": "launchprbstest",
  "tgid": "...", "towers": "...", "timestamp": "...",
  "results": [
    {"func_name": "launchprbstest", "timestamp": 1790865865, "result": {...}}
  ]
}
```

A message is stored only if:

- all nine envelope keys are present and `results` is a list;
- each result has `func_name`, `timestamp` and `result`;
- `test_id` matches a `name` in `ecal_logger_tests`;
- `run_number` exists in `run_info`;
- `func_name` is at most 30 characters.

Otherwise the whole message goes to `ecal_logger_bad_messages` with the reason and traceback. Storage is all-or-nothing per message.

Only `run_number`, `test_id` and the results are stored; the other envelope fields are validated but not saved.

## Database

Oracle INT2R (CMS integration database), schema `ecal_p2ug_conf_dev`.

| Table | Contents | Written by logger |
|---|---|---|
| `ecal_logger_entries` | One row per result (run, test, function, result JSON, timestamp) | yes |
| `ecal_logger_tests` | Catalogue of known tests | no |
| `ecal_logger_bad_messages` | Rejected payloads | yes |
| `run_info`, `run_keys` | Runs and their configurations | no |
| `towers`, `supermodules`, `sm_tower_mapping` | Detector geometry | no |

For local experiments without Oracle, `python logdb.py` creates all tables in a SQLite file (`junk.db`).

## Development

New data usually requires changes in this order: publisher sends the field → `logmsgHandler.py` / `message_handlers.py` parse and store it → table column added in `logdb.py` and the database → `dash_display.py` displays it. NanoMQ needs no changes.

## Known issues

- Handling of malformed messages is still being fixed.
- `mqttClientOracle.py` shutdown: `stop_event.set()` is called before `msg_queue.join()`, which can hang if messages remain queued. Join first, then set the event.
- "Ready" does not confirm the database login; a wrong password shows up only when the first message is processed.
- `logdb.py`: `Test.run` should be `Mapped[List["Entry"]]`; `towers.id_supermodule` references only part of the composite primary key of `supermodules`.
