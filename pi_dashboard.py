from flask import Flask, render_template_string
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
messages = []

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
        messages.append(data)
        if len(messages) > 20:
            messages.pop(0)
    except:
        pass

client = mqtt.Client(
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("v2v/#")
client.loop_start()

HTML = """
<html>
<head><title>V2V Cloud Dashboard</title></head>
<body>
<h2>Raspberry Pi V2V Dashboard</h2>
<table border="1">
<tr>
<th>Sender</th><th>Type</th><th>Timestamp</th>
</tr>
{% for m in messages %}
<tr>
<td>{{m.sender_id}}</td>
<td>{{m.message_type}}</td>
<td>{{m.timestamp}}</td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, messages=messages[::-1])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
