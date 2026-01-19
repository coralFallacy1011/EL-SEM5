import json
import paho.mqtt.client as mqtt

BROKER = "localhost"
VEHICLES = ["ESP1", "ESP2"]   # add more later

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("ROUTER CONNECTED")
    client.subscribe("v2v/send")
    client.subscribe("v2v/broadcast")

def on_message(client, userdata, msg):
    data = msg.payload.decode()
    payload = json.loads(data)

    sender = payload.get("sender_id")
    topic = msg.topic

    if topic == "v2v/send":
        receiver = "ESP2" if sender == "ESP1" else "ESP1"
        print(f"ROUTING {sender} ? {receiver}")
        client.publish(f"v2v/{receiver}", data)

    elif topic == "v2v/broadcast":
        print(f"BROADCAST from {sender}")
        for v in VEHICLES:
            if v != sender:
                client.publish(f"v2v/{v}", data)

client = mqtt.Client(
    client_id="ROUTER",
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, 1883, 60)
client.loop_forever()
