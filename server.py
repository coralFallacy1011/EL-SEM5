from flask import Flask, request

app = Flask(__name__)

# inbox for each vehicle
inbox = {
    "ESP1": [],
    "ESP2": []
}

@app.route('/send', methods=['POST'])
def send():
    data = request.json
    sender = data["from"]
    receiver = data["to"]
    message = data["msg"]

    print(f"Received from {sender} -> {receiver}: {message}")

    if receiver in inbox:
        inbox[receiver].append(f"{sender}: {message}")
        return "Message routed"
    else:
        return "Unknown receiver", 400

@app.route('/receive/<vehicle_id>', methods=['GET'])
def receive(vehicle_id):
    if vehicle_id not in inbox or len(inbox[vehicle_id]) == 0:
        return "No new message"

    msg = inbox[vehicle_id].pop(0)
    print(f"Delivering to {vehicle_id}: {msg}")
    return msg

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
