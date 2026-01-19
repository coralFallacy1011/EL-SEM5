# -*- coding: utf-8 -*-

from flask import Flask, render_template_string, request, redirect
import paho.mqtt.client as mqtt
import json
import time

app = Flask(__name__)

BROKER = "localhost"
VEHICLES = ["ESP1", "ESP2"]

vehicle_state = {v: "IDLE" for v in VEHICLES}
last_messages = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        sender = payload.get("sender_id", "UNKNOWN")
        mtype = payload.get("message_type", "UNKNOWN")

        last_messages.append(payload)
        if len(last_messages) > 20:
            last_messages.pop(0)

        if mtype == "EXCESS_CHARGE":
            vehicle_state[sender] = "EXCESS_CHARGE"
        elif mtype == "REQUEST_CHARGE":
            vehicle_state[sender] = "REQUESTING_CHARGE"
        elif mtype == "CONFIRMATION_MESSAGE":
            vehicle_state[sender] = "IDLE"

    except Exception as e:
        print("MQTT ERROR:", e)

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
<title>V2V Cloud Control</title>
<meta http-equiv="refresh" content="2">
</head>
<body>

<h2>Raspberry Pi V2V Cloud Dashboard</h2>

<h3>Vehicle States</h3>
<table border="1">
<tr><th>Vehicle</th><th>State</th><th>Action</th></tr>
{% for v, s in states.items() %}
<tr>
<td>{{v}}</td>
<td>{{s}}</td>
<td>
{% if s == "EXCESS_CHARGE" %}
<form method="post" action="/assign">
<input type="hidden" name="target" value="{{v}}">
<button type="submit">Send Charge Request</button>
</form>
{% else %}
-
{% endif %}
</td>
</tr>
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

@app.route("/assign", methods=["POST"])
def assign():
    target = request.form["target"]

    msg = {
        "message_type": "REQUEST_CHARGE",
        "sender_id": "PI_CLOUD",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    mqttc.publish(f"v2v/{target}", json.dumps(msg))
    print("PI -> Sent REQUEST_CHARGE to", target)

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
