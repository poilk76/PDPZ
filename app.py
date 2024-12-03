from flask import Flask, render_template, json, request
from flask_socketio import SocketIO
import os
from random import randint,choice
import serial
import multiprocessing

app = Flask(__name__)
io = SocketIO(app)
socket = serial.Serial()

def shuffle_list(lst):
    shuffled = lst[:]  # Create a copy to avoid modifying the original
    n = len(shuffled)
    for i in range(n - 1, 0, -1):  # Start from the end of the list and move backward
        j = randint(0, i)  # Pick a random index from 0 to i
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]  # Swap the elements
    return shuffled

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/table")
def table_screen():
    io.emit("set",{"html":render_template('table.html', len=len(players), players=players),"style":"table"})
    return "Done!"


# losowanie
@app.route("/wheel")
def wheel_screen():
    global questions
    global question_index
    global answering
    if question_index < len(questions)-1:
        question_index += 1
    else:
        questions = shuffle_list(questions)
        question_index = 0
    categories_list = [choice(questions)["category"] for _ in range(7)]
    categories_list.append(questions[question_index]["category"])
    categories_list = shuffle_list(categories_list)
    answering = 0
    io.emit("set",{"html":render_template('wheel.html', categories=categories_list, winner=questions[question_index]["category"],points=questions[question_index]["points"]),"roll":True,"style":"fortune-wheel","pos":categories_list.index(questions[question_index]["category"])})
    return "Done!"


@app.route("/sign",methods=['GET'])
def sign():
    global answering
    if answering != None and request.args["effect"] == "None":
        io.emit("set",{"html":render_template('sign.html', question=questions[question_index]["text"], player=players[answering]["name"]),"roll":False,"style":"sign-container"})
    if request.args["player"] != "None" and answering == None:
        answering = int(request.args["player"])
    elif request.args["effect"] != "None" and answering != None:
        if request.args["effect"] == "1":
            players[answering]["points"] += questions[question_index]["points"]
            io.emit("answer", {"effect":True})
        else:
            players[answering]["points"] -= questions[question_index]["points"]
            io.emit("answer", {"effect":False})
        answering=None

    return "Done!"

def question_screen():
    io.emit("")

def answer_result():
    pass

def new_round():
    socket.write("NR".encode())

@app.route("/name", methods=['GET'])
def name():
    players[int(request.args["player"])]["name"] = str(request.args["change"])
    return "Done!"

@app.route("/points",methods=['GET'])
def points():
    players[int(request.args["player"])]["points"] = int(request.args["change"])
    return "Done!"

@app.route("/admin")
def admin():
    return render_template('admin.html',len=len(players),players=players,question=questions[question_index])

@app.route("/new",methods=['GET'])
def new():
    if request.args["status"] == "1":
        players.append({"name":"name","points":0})
    else:
        players.pop(int(request.args["player"]))
    return "Done!"

def test():
    global answering

    answering = 0

if __name__ == "__main__":
    answering = None
    players = [
        {
            "name":"Dummy",
            "points":0
        }
    ]
    question_index = 0
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "Static/data", "questions.json")
    questions = shuffle_list(json.load(open(json_url)))
    print(questions)

    process = multiprocessing.Process(target=test)
    process.start()
    app.run(host="0.0.0.0", port=8080)
    print(answering)
    process.join()
    