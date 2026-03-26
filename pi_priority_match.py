# coding: utf-8

from flask import Flask, render_template_string
import paho.mqtt.client as mqtt
import json
import time
import math

app = Flask(__name__)

BROKER = "localhost"
VEHICLES = ["ESP1", "ESP2", "ESP3"]

vehicle_state = {v: "IDLE" for v in VEHICLES}
vehicle_data = {}   # lat, lon, charge
last_messages = []

# ---------- DISTANCE FUNCTION (HAVERSINE) ----------

def distance(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ---------- PRIORITY MATCH ----------

def try_priority_match(client):
    requesters = [v for v, s in vehicle_state.items() if s == "REQUESTING_CHARGE"]
    donors = [v for v, s in vehicle_state.items() if s == "EXCESS_CHARGE"]

    if not requesters or not donors:
        return

    requester = requesters[0]
    rdata = vehicle_data.get(requester)
    if not rdata:
        return

    best_donor = None
    best_score = -999999

    for d in donors:
        ddata = vehicle_data.get(d)
        if not ddata:
            continue

        dist = distance(
            rdata["lat"], rdata["lon"],
            ddata["lat"], ddata["lon"]
        )

        score = (2 * ddata["charge"]) - (5 * dist)

        print(f"CHECK {d}: charge={ddata['charge']} dist={dist:.2f} score={score:.2f}")

        if score > best_score:
            best_score = score
            best_donor = d

    if best_donor:
        print(f"SELECTED DONOR: {best_donor} for {requester}")

        msg = {
            "message_type": "REQUEST_CHARGE",
            "sender_id": "PI_CLOUD",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        client.publish(f"v2v/{best_donor}", json.dumps(msg))

        vehicle_state[best_donor] = "BUSY"
        vehicle_state[requester] = "BUSY"

# ---------- MQTT CALLBACK ----------

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        sender = payload.get("sender_id")
        mtype = payload.get("message_type")

        last_messages.append(payload)
        if len(last_messages) > 30:
            last_messages.pop(0)

        if sender not in vehicle_state:
            return

        vehicle_data[sender] = {
            "lat": payload.get("lat", 0),
            "lon": payload.get("lon", 0),
            "charge": payload.get("charge", 0)
        }

        if mtype == "EXCESS_CHARGE":
            vehicle_state[sender] = "EXCESS_CHARGE"

        elif mtype == "REQUEST_CHARGE":
            vehicle_state[sender] = "REQUESTING_CHARGE"

        elif mtype == "CONFIRMATION_MESSAGE":
            vehicle_state[sender] = "IDLE"

        try_priority_match(client)

    except Exception as e:
        print("ERROR:", e)

# ---------- MQTT SETUP ----------

mqttc = mqtt.Client(
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

mqttc.on_message = on_message
mqttc.connect(BROKER, 1883)
mqttc.subscribe("v2v/#")
mqttc.loop_start()

# ---------- WEB UI ----------

HTML = """
<html>
<head>
<title>Priority Matching Dashboard</title>
<meta http-equiv="refresh" content="2">
</head>
<body>

<h2>V2V Priority + Distance Matching</h2>

<table border="1">
<tr><th>Vehicle</th><th>State</th><th>Charge</th><th>Lat</th><th>Lon</th></tr>
{% for v, s in states.items() %}
<tr>
<td>{{v}}</td>
<td>{{s}}</td>
<td>{{data[v].charge if v in data else '-'}}</td>
<td>{{data[v].lat if v in data else '-'}}</td>
<td>{{data[v].lon if v in data else '-'}}</td>
</tr>
{% endfor %}
</table>

<h3>Recent Messages</h3>
<ul>
{% for m in messages %}
<li>{{m.sender_id}} {{m.message_type}} {{m.timestamp}}</li>
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
        data=vehicle_data,
        messages=reversed(last_messages)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
