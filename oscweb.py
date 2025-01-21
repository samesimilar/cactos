#!python3
#
# oscweb.py
# Copyright 2025 Michael Spears (mws@samesimilar.com)
# See LICENSE.
#
# Enables communication between OSC (https://opensoundcontrol.org) and a web browser via a WebSocket (https://websockets.spec.whatwg.org)
#
# web browser <---> [websocket port 8002] <---> oscweb [OSC protocol] <--- Pd net send [port 4002]  e.g. Pd (puredata.info)
#                                                                    |---> Pd net receive [port 4000]
# Installing:
# This method isolates the package dependencies in a local virtual environment.
# https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#create-and-use-virtual-environments
# - `cd /path/to/project`
# - create virtual environment: `python3 -m venv .venv`
# - activate virtual environment: `source .venv/bin/activate`
# - install requirements: `python3 -m pip install -r requirements.txt`
# - run: `python3 oscweb.py`
#
# Default Ports (These details can be changed in the variables below.)
# 
# - Pd should receive incoming OSC messages on UDP port 4000.
# - PD should send outgoing OSC messages to 127.0.0.1 on UDP port 4002.
# - The browser should connect to the WebSocket server on port 8002.




import asyncio
import json
import base64

from websockets.asyncio.server import broadcast, serve

from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer

# Connection sites:
internal_osc_pd_side_ip = "127.0.0.1"
internal_osc_python_side_ip = "127.0.0.1"
internal_osc_pd_side_port = 4000
internal_osc_python_side_port = 4002
external_websocket_interface_ip = "127.0.0.1"
external_websocket_port = 8002



dispatcher = Dispatcher()
osc_client = udp_client.SimpleUDPClient(internal_osc_pd_side_ip, internal_osc_pd_side_port)
print(f"Opening OSC client to send to Pd at {internal_osc_pd_side_ip}:{internal_osc_pd_side_port}")

# current websocket clients
CONNECTIONS = set()

def bytes_to_base64_string(value: bytes):
	if value.__class__.__name__ != 'bytes':
		return value
	
	return {"base64":base64.b64encode(value).decode('ASCII')}
   
def osc_callback(address, *args) -> None:
	args = [bytes_to_base64_string(v) for v in args]
		
	d = {
		"address": address,
		"v": args
	}
	j = json.dumps(d)
	# print(j)
	broadcast(CONNECTIONS, j)
	

# websockets.server.serve runs echo for each new connection
# it closes a connection when this function returns
async def echo(websocket):
	print(f"WebSocket connection [{websocket.id}]:{websocket.remote_address} initiated")
	CONNECTIONS.add(websocket)
	#this loop exits if the client disconnects
	async for message in websocket:		
		obj = json.loads(message)				
		osc_client.send_message(obj["address"], obj["v"])
	CONNECTIONS.remove(websocket)
	print(f"[{websocket.id}]:{websocket.remote_address} connection closed")
	

async def main():
	dispatcher.set_default_handler(osc_callback)
	osc_server = AsyncIOOSCUDPServer((internal_osc_python_side_ip, internal_osc_python_side_port), dispatcher, asyncio.get_running_loop())
	transport, protocol = await osc_server.create_serve_endpoint()  # Create datagram endpoint and start serving
	print(f"Created OSC server to listen to Pd at {internal_osc_python_side_ip}:{internal_osc_python_side_port}")
	async with serve(echo, external_websocket_interface_ip, external_websocket_port):
		print(f"Created WebSocket server on {external_websocket_interface_ip}:{external_websocket_port}")
		print("")
		print("Leave this script running and open index.html in browser window. Press ctrl+c to stop the server.")
		await asyncio.get_running_loop().create_future()  # run forever

if __name__ == "__main__":
	asyncio.run(main())
	