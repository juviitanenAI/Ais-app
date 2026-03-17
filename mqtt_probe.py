import ssl, time, json
import paho.mqtt.client as mqtt

BROKER = "meri.digitraffic.fi"   # try "meri-test.digitraffic.fi" if needed
PORT = 443
PATH = "/mqtt"

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected with rc =", rc)
    if rc == 0:
        client.subscribe("vessels-v2/+/location")
        client.subscribe("vessels-v2/+/metadata")
        print("Subscribed to AIS topics")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        payload = msg.payload[:120]
    print(f"[MSG] {msg.topic}: {payload}")

client = mqtt.Client(transport="websockets")
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
client.ws_set_options(path=PATH)
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, keepalive=60)
client.loop_start()
time.sleep(20)
client.loop_stop()
client.disconnect()