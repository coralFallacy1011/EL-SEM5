# coding: utf-8
import paho.mqtt.client as mqtt
import json, time
from flask import Flask

BROKER = "localhost"

VEHICLE_DB = {
    "ESP1": {"car":"DL16BC6425","phone":"+911111111111"},
    "ESP2": {"car":"KA05MN1234","phone":"+922222222222"}
}

runtime = {}
assigned = False

def on_message(client, userdata, msg):
    global assigned
    data = json.loads(msg.payload.decode())
    t = data.get("message_type")
    sender = data.get("sender_id")

    if sender:
        runtime[sender] = data

    if t == "REQUEST_CHARGE":
        offer = {
            "message_type":"CHARGE_OFFER",
            "requester_id":sender,
            "lat":data["lat"],
            "lon":data["lon"],
            "timestamp":time.strftime("%F %T")
        }
        client.publish("v2v/broadcast", json.dumps(offer))
        assigned = False

    elif t == "ACCEPT_CHARGE" and not assigned:
        donor = sender
        req = data["requester_id"]

        conf = {
            "message_type":"CONFIRMATION_MESSAGE",

            "donor_id": donor,
            "donor_car": VEHICLE_DB[donor]["car"],
            "donor_phone": VEHICLE_DB[donor]["phone"],
            "donor_lat": runtime[donor]["lat"],
            "donor_lon": runtime[donor]["lon"],

            "requester_id": req,
            "requester_car": VEHICLE_DB[req]["car"],
            "requester_phone": VEHICLE_DB[req]["phone"],
            "requester_lat": runtime[req]["lat"],
            "requester_lon": runtime[req]["lon"],

            "timestamp": time.strftime("%F %T")
        }

        client.publish("v2v/broadcast", json.dumps(conf))
        assigned = True

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_message = on_message
mqttc.connect(BROKER,1883)
mqttc.subscribe("v2v/#")
mqttc.loop_forever()
