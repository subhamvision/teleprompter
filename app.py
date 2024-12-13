from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from data.classes import classes_data
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*")

# Track room statuses and messages
active_rooms = {}
room_messages = {}


@app.route("/")
def index():
    return render_template("class_list.html", classes=classes_data)


@app.route("/join_class", methods=["GET"])
def join_class():
    room = request.args.get("room")
    role = request.args.get("role")

    if not room or not role:
        return "Room and role are required", 400

    if role == "receiver":
        active_rooms[room] = {"receiver": True, "sender": False}
        room_messages[room] = []
        return jsonify({"redirect": f"/page2?room={room}"}), 200

    elif role == "sender":
        if active_rooms.get(room, {}).get("receiver"):
            active_rooms[room]["sender"] = True
            return jsonify({"roomReady": True, "redirect": f"/page1?room={room}"}), 200
        else:
            return (
                jsonify(
                    {
                        "roomReady": False,
                        "message": f"Receiver has not joined room {room} yet.",
                    }
                ),
                200,
            )

    return "Invalid role", 400


@app.route("/page1")
def page1():
    room = request.args.get("room")
    return render_template("page1.html", room=room)


@app.route("/page2")
def page2():
    room = request.args.get("room")
    return render_template("page2.html", room=room)


@socketio.on("join_room")
def handle_join(data):
    room = data["room"]
    role = data["role"]
    join_room(room)

    if role == "receiver":
        active_rooms[room]["receiver"] = True
        emit("room_status", {"receiverPresent": True}, room=room)

    elif role == "sender":
        emit(
            "room_status",
            {"receiverPresent": active_rooms[room]["receiver"]},
            room=request.sid,
        )


@socketio.on("disconnect")
def on_disconnect():
    for room, roles in active_rooms.items():
        # print(room)
        # print(roles)
        if request.sid in socketio.server.manager.rooms["/"]:
            role = "receiver" if roles.get("receiver") else "sender"
            roles[role] = False
            if role == "receiver":
                emit("room_status", {"receiverPresent": False}, room=room)
            break


@socketio.on("send_message")
def handle_message(data):
    room = data["room"]
    message = data["message"]

    # Store the message in room's history
    room_messages[room].append(message)
    emit("receive_message", message, room=room)


@socketio.on("clear_messages")
def clear_messages(data):
    room = data["room"]
    room_messages[room] = []
    emit("clear", room=room)


@socketio.on("get_messages")
def get_messages(data):
    room = data["room"]
    emit("message_history", room_messages.get(room, []))


if __name__ == "__main__":
    socketio.run(app, debug=True)
