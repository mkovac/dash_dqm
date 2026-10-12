from logdb import *

from dash import Dash, html, dcc, Input, Output, Patch, callback, clientside_callback
import dash_ag_grid as dag
import datetime

import os
import pathlib
import argparse
import getpass

import sqlalchemy
from sqlalchemy import create_engine

parser = argparse.ArgumentParser('Dash Display Test for Rundbv2')
parser.add_argument('-f', '--db', default='junk.db', type=str, help='SQLite Database file')
parser.add_argument('-o', '--oracle', action='store_true', help='Connect to Oracle Database')
parser.add_argument('-p', '--port', default=8050, type=int, help='Port to serve the dashboard on')
args = parser.parse_args()


# ---------------------------------------------------------------- database

try:
    if args.oracle:
        import oracledb
        oracledb.init_oracle_client()

        connectS = ("(DESCRIPTION = (ADDRESS=(PROTOCOL = TCP)(HOST = int2r-s.cern.ch)(PORT = 10121))"
                    "(CONNECT_DATA= (SERVICE_NAME = int2r_lb.cern.ch)(SERVER = DEDICATED)))")
        print(f'Trying to connect to oracle using {connectS}')
        dbEngine = create_engine("oracle+oracledb://", connect_args={
            "user": "ecal_p2ug_conf_dev",
            # password from ECAL_DB_PASSWORD if set, otherwise prompt
            "password": os.environ.get('ECAL_DB_PASSWORD') or getpass.getpass(),
            "dsn": connectS})
        session = Session(dbEngine)
        sourceLabel = 'Oracle · int2r_lb.cern.ch'
    else:
        path = pathlib.Path(args.db)
        if not path.exists():
            print(f'Error database {path} does not exist!')
            exit()
        print(f'Opening {path.absolute()}')
        dbEngine = create_engine(f'sqlite:///{path.absolute()}', connect_args={'autocommit': True})
        session = Session(dbEngine)
        session.execute(sqlalchemy.text("PRAGMA foreign_keys=ON"))
        sourceLabel = f'SQLite · {path.name}'
    # Databases created before BadMessage was added to logdb do not have this table
    hasBadMessages = sqlalchemy.inspect(dbEngine).has_table(BadMessage.__tablename__)
except Exception as e:
    print(f'Error opening dB {e}')
    exit()


def fmt_time(t):
    """Datetime or unix timestamp -> readable string."""
    if isinstance(t, (int, float)):
        t = datetime.datetime.fromtimestamp(t)
    return t.strftime('%Y-%m-%d %H:%M:%S') if isinstance(t, datetime.datetime) else str(t or '')


def load_data():
    """Read runs, entries and bad messages. 'id' is the (unique, string) grid row id."""
    session.expire_all()
    runs = [{'id': str(r.run_number), 'run_number': r.run_number, 'supermodule': r.sm,
             'location': r.location,
             'starttime': fmt_time(r.starttime), 'endtime': fmt_time(r.endtime),
             'entries': len(r.entries)}
            for r in session.execute(select(RunInfo)).scalars()]
    entries = [{'id': f'{e.run_number}-{e.entry_id}', 'run_number': e.run_number,
                'entry_id': e.entry_id, 'test_name': e.test.name,
                'test_description': e.test.description, 'func_name': e.func_name,
                'results': e.result, 'timestamp': fmt_time(e.test_timestamp)}
               for e in session.execute(select(Entry)).scalars()]
    nTests = len(session.execute(select(Test)).scalars().all())
    bad = [{'id': str(m.bad_message_id), 'received_at': fmt_time(m.received_at), 'topic': m.topic,
            'reason': m.reason, 'exception': m.exception, 'payload': m.payload}
           for m in session.execute(select(BadMessage)).scalars()] if hasBadMessages else []
    return runs, entries, nTests, bad


# ------------------------------------------------------------------ layout

runColumns = [
    {'headerName': 'Run #', 'field': 'run_number', 'sort': 'desc', 'maxWidth': 95},
    {'headerName': 'Supermodule', 'field': 'supermodule', 'maxWidth': 120},
    {'headerName': 'Location', 'field': 'location', 'maxWidth': 110},
    {'headerName': 'Start', 'field': 'starttime', 'minWidth': 170},
    {'headerName': 'End', 'field': 'endtime', 'minWidth': 170},
    {'headerName': 'Entries', 'field': 'entries', 'maxWidth': 95, 'type': 'rightAligned'},
]

# Result strings (lower case) shown in green / red
OK = ['pass', 'passed', 'ok', 'true', 'success', '1']
BAD = ['fail', 'failed', 'error', 'false', '0']

entryColumns = [
    {'headerName': 'Run #', 'field': 'run_number', 'maxWidth': 95},
    {'headerName': 'Entry', 'field': 'entry_id', 'maxWidth': 95},
    {'headerName': 'Test', 'field': 'test_name', 'tooltipField': 'test_description'},  # hover = description
    {'headerName': 'Function', 'field': 'func_name'},
    {'headerName': 'Result', 'field': 'results', 'cellClassRules': {
        'cell-ok': f"{OK}.includes(('' + params.value).toLowerCase())",
        'cell-bad': f"{BAD}.includes(('' + params.value).toLowerCase())"}},
    {'headerName': 'Timestamp', 'field': 'timestamp', 'sort': 'desc', 'minWidth': 170},
]


# Messages the logger could not store; hover a cell to read long text in full
badColumns = [
    {'headerName': 'Received', 'field': 'received_at', 'sort': 'desc', 'minWidth': 170, 'maxWidth': 190},
    {'headerName': 'Topic', 'field': 'topic', 'tooltipField': 'topic'},
    {'headerName': 'Reason', 'field': 'reason', 'tooltipField': 'reason', 'flex': 2},
    {'headerName': 'Exception', 'field': 'exception', 'tooltipField': 'exception', 'flex': 2},
    {'headerName': 'Payload', 'field': 'payload', 'tooltipField': 'payload', 'flex': 3},
]


def grid(grid_id, columnDefs, height='520px', **options):
    return dag.AgGrid(
        id=grid_id, rowData=[], columnDefs=columnDefs, getRowId='params.data.id',
        defaultColDef={'sortable': True, 'filter': True, 'resizable': True, 'flex': 1, 'minWidth': 80},
        dashGridOptions={'pagination': True, 'paginationPageSize': 20, 'animateRows': True,
                         'tooltipShowDelay': 300, **options},
        className='ag-theme-alpine', style={'height': height, 'width': '100%'})


def kpi(label, value_id):
    return html.Div(className='kpi', children=[
        html.Div(label, className='kpi-label'),
        html.Div('–', id=value_id, className='kpi-value')])


def card(head, body):
    return html.Div(className='card', children=[html.Div(head, className='card-head'), body])


CSS = '''
:root { --bg:#f4f6f9; --panel:#fff; --border:#e2e6ec; --text:#1b2430; --muted:#6b7686;
        --accent:#2563eb; --ok:#15803d; --bad:#b91c1c; }
:root[data-theme="dark"] { --bg:#0f141b; --panel:#171e27; --border:#263040; --text:#e6eaf0;
        --muted:#8b97a8; --accent:#60a5fa; --ok:#4ade80; --bad:#f87171; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-size:14px;
       font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
.topbar { display:flex; align-items:center; gap:12px; flex-wrap:wrap; padding:14px 24px;
          background:var(--panel); border-bottom:1px solid var(--border); }
.topbar h1 { font-size:18px; font-weight:600; margin:0; }
.badge { font-size:12px; color:var(--muted); border:1px solid var(--border);
         border-radius:999px; padding:3px 10px; }
.spacer { flex:1; }
.updated, .hint { font-size:12px; color:var(--muted); }
.btn { font:inherit; color:var(--text); background:var(--panel); border:1px solid var(--border);
       border-radius:8px; padding:7px 14px; cursor:pointer; }
.btn:hover { border-color:var(--accent); }
.btn.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
.content { padding:20px 24px; max-width:1800px; margin:0 auto; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin-bottom:18px; }
.kpi, .card { background:var(--panel); border:1px solid var(--border); border-radius:12px; }
.kpi { padding:14px 18px; }
.kpi-label { font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
.kpi-value { font-size:26px; font-weight:600; margin-top:4px; font-variant-numeric:tabular-nums; }
.grids { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:18px; }
@media (max-width:1100px) { .grids { grid-template-columns:minmax(0,1fr); } }
.card { padding:16px; }
.grids { margin-bottom:18px; }
.card-head { display:flex; align-items:center; gap:10px; margin-bottom:12px; flex-wrap:wrap; }
.card-head h2 { font-size:15px; font-weight:600; margin:0; }
.search { font:inherit; color:var(--text); background:var(--bg); border:1px solid var(--border);
          border-radius:8px; padding:7px 12px; width:220px; }
.search:focus { outline:none; border-color:var(--accent); }
.cell-ok { color:var(--ok); font-weight:600; }
.cell-bad { color:var(--bad); font-weight:600; }
.ag-root-wrapper { border-radius:8px; }
.card [class*="ag-theme"], .card .ag-root-wrapper { color-scheme:light;   /* grid colours follow the page theme */
    --ag-background-color:var(--panel); --ag-header-background-color:var(--bg);
    --ag-odd-row-background-color:var(--panel); --ag-row-hover-color:var(--bg);
    --ag-foreground-color:var(--text); --ag-text-color:var(--text); --ag-data-color:var(--text);
    --ag-header-foreground-color:var(--text); --ag-header-text-color:var(--text);
    --ag-secondary-foreground-color:var(--muted); --ag-border-color:var(--border);
    --ag-row-border-color:var(--border); --ag-menu-background-color:var(--panel);
    --ag-control-panel-background-color:var(--panel); --ag-input-border-color:var(--border);
    --ag-selected-row-background-color:color-mix(in srgb, var(--accent) 18%, var(--panel)); }
:root[data-theme="dark"] .card [class*="ag-theme"], :root[data-theme="dark"] .card .ag-root-wrapper { color-scheme:dark; }
'''

dashApp = Dash(__name__, title='ECAL Run DB')
dashApp.index_string = dashApp.index_string.replace('{%css%}', '{%css%}<style>' + CSS + '</style>')

dashApp.layout = html.Div([
    dcc.Store(id='entries-store'),
    dcc.Store(id='theme-store', storage_type='local', data='light'),

    html.Div(className='topbar', children=[
        html.H1('ECAL Run DB'),
        html.Span(sourceLabel, className='badge'),
        html.Div(className='spacer'),
        html.Span(id='last-updated', className='updated'),
        html.Button('Dark mode', id='theme-btn', className='btn'),
        html.Button('Refresh', id='refresh-btn', className='btn primary'),
    ]),

    html.Div(className='content', children=[
        html.Div(className='kpis', children=[
            kpi('Runs', 'kpi-runs'),
            kpi('Test entries', 'kpi-entries'),
            kpi('Defined tests', 'kpi-tests'),
            kpi('Latest run', 'kpi-latest'),
            kpi('Bad messages', 'kpi-bad'),
        ]),
        html.Div(className='grids', children=[
            card([html.H2('Run Infos'),
                  html.Span('Click a run to show only its entries', className='hint'),
                  html.Div(className='spacer'),
                  html.Button('Show all', id='clear-btn', className='btn')],
                 grid('runs-grid', runColumns, rowSelection='single')),
            card([html.H2('Test Entries', id='entries-title'),
                  html.Div(className='spacer'),
                  dcc.Input(id='search', type='text', placeholder='Search entries…', className='search')],
                 grid('entries-grid', entryColumns)),
        ]),
        card([html.H2('Bad Messages'),
              html.Span('Messages the logger received but could not store' if hasBadMessages
                        else 'This database has no bad-messages table', className='hint')],
             grid('bad-grid', badColumns, height='360px')),
    ]),
])


# --------------------------------------------------------------- callbacks

@callback(
    Output('runs-grid', 'rowData'),
    Output('entries-store', 'data'),
    Output('kpi-runs', 'children'),
    Output('kpi-entries', 'children'),
    Output('kpi-tests', 'children'),
    Output('kpi-latest', 'children'),
    Output('bad-grid', 'rowData'),
    Output('kpi-bad', 'children'),
    Output('last-updated', 'children'),
    Input('refresh-btn', 'n_clicks'),
)
def refresh(_):
    """Runs on page load and on every Refresh click."""
    runs, entries, nTests, bad = load_data()
    latest = max((r['run_number'] for r in runs), default='–')
    stamp = datetime.datetime.now().strftime('Updated %H:%M:%S')
    return runs, entries, len(runs), len(entries), nTests, latest, bad, len(bad), stamp


@callback(
    Output('entries-grid', 'rowData'),
    Output('entries-title', 'children'),
    Input('entries-store', 'data'),
    Input('runs-grid', 'selectedRows'),
)
def show_entries(entries, selected):
    """Show all entries, or only those of the selected run."""
    entries = entries or []
    if not selected:
        return entries, 'Test Entries · All runs'
    run = selected[0]['run_number']
    return [e for e in entries if e['run_number'] == run], f'Test Entries · Run {run}'


@callback(Output('runs-grid', 'selectedRows'), Input('clear-btn', 'n_clicks'), prevent_initial_call=True)
def clear_selection(_):
    return []


@callback(Output('entries-grid', 'dashGridOptions'), Input('search', 'value'), prevent_initial_call=True)
def search_entries(text):
    options = Patch()
    options['quickFilterText'] = text or ''
    return options


# Dark/light toggle, done in the browser and remembered there
clientside_callback(
    """
    function(n, theme) {
        const clicked = dash_clientside.callback_context.triggered.some(t => t.prop_id.startsWith('theme-btn'));
        if (clicked) theme = theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        return [theme, theme === 'dark' ? 'Light mode' : 'Dark mode'];
    }
    """,
    Output('theme-store', 'data'),
    Output('theme-btn', 'children'),
    Input('theme-btn', 'n_clicks'),
    Input('theme-store', 'data'),
)


if __name__ == '__main__':
    dashApp.run(debug=True, use_reloader=False, port=args.port)
