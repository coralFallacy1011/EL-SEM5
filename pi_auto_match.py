# coding: utf-8

from flask import Flask, render_template_string
import paho.mqtt.client as mqtt
import json
import time

app = Flask(__name__)

BROKER = "localhost"
VEHICLES = ["ESP1", "ESP2", "ESP3"]

vehicle_state = {v: "IDLE" for v in VEHICLES}
last_messages = []

def try_auto_match(client):
    excess = [v for v, s in vehicle_state.items() if s == "EXCESS_CHARGE"]
    request = [v for v, s in vehicle_state.items() if s == "REQUESTING_CHARGE"]

    if excess and request:
        giver = excess[0]
        receiver = request[0]

        print("AUTO MATCH:", giver, "->", receiver)

        msg = {
            "message_type": "REQUEST_CHARGE",
            "sender_id": "PI_CLOUD",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        client.publish("v2v/" + giver, json.dumps(msg))

        vehicle_state[giver] = "BUSY"
        vehicle_state[receiver] = "BUSY"

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        sender = payload.get("sender_id")
        mtype = payload.get("message_type")

        last_messages.append(payload)
        if len(last_messages) > 25:
            last_messages.pop(0)

        if sender not in vehicle_state:
            return

        if mtype == "EXCESS_CHARGE":
            vehicle_state[sender] = "EXCESS_CHARGE"

        elif mtype == "REQUEST_CHARGE":
            vehicle_state[sender] = "REQUESTING_CHARGE"

        elif mtype == "CONFIRMATION_MESSAGE":
            vehicle_state[sender] = "IDLE"

        try_auto_match(client)

    except Exception as e:
        print("ERROR:", e)

mqttc = mqtt.Client(
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

mqttc.on_message = on_message
mqttc.connect(BROKER, 1883)
mqttc.subscribe("v2v/#")
mqttc.loop_start()

HTML = """
<html>
<head>
<title>V2V Auto Match Dashboard</title>
<meta http-equiv="refresh" content="2">
</head>
<body>

<h2>Raspberry Pi Auto Matching Controller</h2>

<table border="1">
<tr><th>Vehicle</th><th>State</th></tr>
{% for v, s in states.items() %}
<tr><td>{{v}}</td><td>{{s}}</td></tr>
{% endfor %}
</table>

<h3>Recent Messages</h3>
<ul>
{% for m in messages %}
<li>{{m.sender_id}} -> {{m.message_type}} @ {{m.timestamp}}</li>
{% endfor %}
</ul>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(
        HTML,
        states=vehicle_state,
        messages=reversed(last_messages)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
