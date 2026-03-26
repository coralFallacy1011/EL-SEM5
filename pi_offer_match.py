# coding: utf-8

from flask import Flask, render_template_string
import paho.mqtt.client as mqtt
import json
import time

app = Flask(__name__)

BROKER = "localhost"
VEHICLES = ["ESP1", "ESP2", "ESP3"]

# -------- STATIC VEHICLE INFO (SIMULATED DATABASE) --------
# In real system this comes from registration backend
vehicle_registry = {
    "ESP1": {
        "car_no": "DL16BC6425",
        "phone": "+91XXXXXXXXXX"
    },
    "ESP2": {
        "car_no": "KA03AB9876",
        "phone": "+91YYYYYYYYYY"
    },
    "ESP3": {
        "car_no": "KA05MN1234",
        "phone": "+91ZZZZZZZZZZ"
    }
}

# -------- STATE --------
vehicle_state = {v: "IDLE" for v in VEHICLES}
vehicle_runtime_data = {}   # lat, lon, charge
active_request = None       # requester id
assigned = False
last_messages = []

# -------- BROADCAST OFFER --------
def broadcast_offer(client, requester, lat, lon):
    global active_request, assigned

    active_request = requester
    assigned = False

    offer = {
        "message_type": "CHARGE_OFFER",
        "requester_id": requester,
        "lat": lat,
        "lon": lon,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    print("PI: Broadcasting charge offer for", requester)
    client.publish("v2v/broadcast", json.dumps(offer))

# -------- MQTT CALLBACK --------
def on_message(client, userdata, msg):
    global assigned

    try:
        payload = json.loads(msg.payload.decode())
        mtype = payload.get("message_type")
        sender = payload.get("sender_id")

        last_messages.append(payload)
        if len(last_messages) > 40:
            last_messages.pop(0)

        # ---- STORE RUNTIME DATA ----
        if sender:
            vehicle_runtime_data[sender] = {
                "lat": payload.get("lat"),
                "lon": payload.get("lon"),
                "charge": payload.get("charge")
            }

        # ---- REQUEST CHARGE ----
        if mtype == "REQUEST_CHARGE":
            vehicle_state[sender] = "REQUESTING_CHARGE"
            broadcast_offer(
                client,
                sender,
                payload.get("lat"),
                payload.get("lon")
            )

        # ---- EXCESS CHARGE ----
        elif mtype == "EXCESS_CHARGE":
            vehicle_state[sender] = "EXCESS_CHARGE"

        # ---- ACCEPT CHARGE ----
        elif mtype == "ACCEPT_CHARGE" and not assigned:
            donor = sender
            requester = payload.get("requester_id")

            print("PI: Accepted by", donor)

            donor_info = {
                "id": donor,
                "car_no": vehicle_registry[donor]["car_no"],
                "phone": vehicle_registry[donor]["phone"],
                "lat": vehicle_runtime_data.get(donor, {}).get("lat"),
                "lon": vehicle_runtime_data.get(donor, {}).get("lon")
            }

            requester_info = {
                "id": requester,
                "car_no": vehicle_registry[requester]["car_no"],
                "phone": vehicle_registry[requester]["phone"],
                "lat": vehicle_runtime_data.get(requester, {}).get("lat"),
                "lon": vehicle_runtime_data.get(requester, {}).get("lon")
            }

            confirmation = {
                "message_type": "CONFIRMATION_MESSAGE",
                "donor": donor_info,
                "requester": requester_info,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            client.publish("v2v/" + donor, json.dumps(confirmation))
            client.publish("v2v/" + requester, json.dumps(confirmation))

            vehicle_state[donor] = "BUSY"
            vehicle_state[requester] = "BUSY"
            assigned = True

    except Exception as e:
        print("PI ERROR:", e)

# -------- MQTT SETUP --------
mqttc = mqtt.Client(
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

mqttc.on_message = on_message
mqttc.connect(BROKER, 1883)
mqttc.subscribe("v2v/#")
mqttc.loop_start()

# -------- MONITOR DASHBOARD --------
HTML = """
<html>
<head>
<meta http-equiv="refresh" content="2">
<title>Charge Offer Controller</title>
</head>
<body>

<h2>Pi Charge Offer Controller</h2>

<h3>Vehicle States</h3>
<ul>
{% for v,s in states.items() %}
<li>{{v}} : {{s}}</li>
{% endfor %}
</ul>

<h3>Recent Messages</h3>
<ul>
{% for m in messages %}
<li>{{m.message_type}}</li>
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
