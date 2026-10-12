import paho.mqtt.client as paho

import msggen




import argparse

parser = argparse.ArgumentParser('Send some fake messages')

parser.add_argument('-n', '--run', type=int, default = 1, help='Run number to use')
parser.add_argument('-t', '--test', type=str, choices=msggen.test_ids.keys(), help='Test To Run', default="")
parser.add_argument('-g', '--testgroup', type=str, default='test_tt', help='Test Group')
parser.add_argument('--host', type=str, default='localhost', help='Address or IP to connect to')
parser.add_argument('--stop', action='store_true', default=False, help='send stop to control')

args = parser.parse_args()

msg = None 
if args.test == "":
    print('Generating Random Test')
    msg = msggen.random_bcp_message(run_number=args.run, test_group=args.testgroup)
else:
    print('Not implemented, gen random')
    msg = msggen.random_bcp_message(run_number=args.run, test_group=args.testgroup)

client = None 
try:
    client = paho.Client(client_id='', userdata=None, protocol=paho.MQTTv5)
    client.connect(args.host)

    path = f'runs/{args.run}/{args.testgroup}'
    client.publish(path, msg.json())

    if args.stop:
        path = 'control/bcp1'
        client.publish(path, 'stop')
    
except Exception as e:
    print(e)
    exit()

