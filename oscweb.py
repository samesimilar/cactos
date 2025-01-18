#!python3
# installing:
# https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#create-and-use-virtual-environments
# - create virtual environment: `python3 -m venv .venv`
# - activate virtual environment: `source .venv/bin/activate`
# - install requirements: `python3 -m pip install -r requirements.txt`



import asyncio
import json
from websockets.server import broadcast, serve
from pythonosc import udp_client
import base64

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer

internal_osc_pd_side_ip = "127.0.0.1"
internal_osc_python_side_ip = "127.0.0.1"
internal_osc_pd_side_port = 4000
internal_osc_python_side_port = 4002
external_websocket_interface_ip = "0.0.0.0"
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
		await asyncio.get_running_loop().create_future()  # run forever

if __name__ == "__main__":
	asyncio.run(main())