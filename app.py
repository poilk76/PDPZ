from flask import Flask, request, render_template
from flask_socketio import SocketIO
from json import loads
from random import shuffle, randint
from multiprocessing import Process,Value
import time
import serial
import requests

class Questions:

    def __init__(self):
        with open("./Static/questions.json", 'r',encoding="UTF-8") as f:
            self.questions = loads(f.read())
        self.index = 0
        shuffle(self.questions)
        self.value = self.questions[self.index]

    def next(self):
        self.index += 1
        self.value = self.questions[self.index]
        if self.index >= len(self.questions)-1:
            shuffle(self.questions)
            self.index = 0


#Zmienne globalne
app = Flask(__name__)
io = SocketIO(app)
answering = None
points = 0
questions = Questions()
players = [
    {
        "name":"Test",
        "points":0
    },
    {
        "name":"maniek",
        "points":20
    }
]

#Zmienne które działają z procesem seriala
shared_answerResult = Value('i',-1)
#stany: 0 - IDLE, 1 - NOWA RUNDA, 2 - CZEKA NA ZGŁOSZENIE, 3 - CZEKA NA DOBRA/ZŁA ODP
shared_state = Value('i', 0)

#Funkcja która działa jako proces w tle
def background_task(shared_answerResult):
    serialInst = serial.Serial("COM3")
    time.sleep(2)
    while True:
        if shared_state.value == 1:
            serialInst.write(b"NR")
            with shared_state.get_lock():
                shared_state.value = 2
        elif shared_state.value == 2:
            input = serialInst.readline()
            index = int(input)
            requests.get(f"http://127.0.0.1:8080/test?func=who&player={index}")
            with shared_state.get_lock():
                shared_state.value = 3
        elif shared_state.value == 3:
            if shared_answerResult.value == 0:
                serialInst.write(b"F")
                with shared_state.get_lock():
                    shared_state.value = 0
            elif shared_answerResult.value == 1:
                serialInst.write(b"T")
                with shared_state.get_lock():
                    shared_state.value = 0

#Funkcje które działają na stronie (można ich używać w bacground_task)
def startGame():
    global questions
    global points
    global answering
    answering = None
    questions.next()
    points = randint(1,5)*100
    data = {"question":questions.value,"html":render_template("content/wheel.html"),"points":points}
    io.emit("start",data)
    time.sleep(3.2)
    with shared_state.get_lock():
        shared_state.value = 1

def whoAnswering(index:int):
    global answering
    answering = index
    data = {"player":players[index]}
    io.emit("answering",data)

def answerResult(result:bool):
    global answering
    if answering != None:
        if result==1:
            players[answering]["points"] += points
        else:
            players[answering]["points"] -= (points/2)
        shared_answerResult.value = int(result)
        io.emit("result",result)
        answering = None

def pointsTable():
    if answering == None:
        data = {"players":sorted(players,key=lambda x: x["points"],reverse=True),"html":render_template("content/table.html")}
        io.emit("table",data)

#Routy dla weba
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def obs():
    return render_template("admin.html",len=len(players),players=players)

@app.route("/phone")
def phone():
    return render_template("phone.html",answer=questions.value["answer"])

@app.route("/players", methods=['GET'])
def playersChanger():
    match request.args["func"]:
        case "add":
            players.append({"name":"Gracz","points":500})
        case "del":
            players.pop(int(request.args["index"]))
        case "name":
            players[int(request.args["index"])]["name"] = request.args["value"]
        case "points":
            players[int(request.args["index"])]["points"] = int(request.args["value"])

#Funkcja do testowania (użycie 127.0.0.1:8080/test?func=[jaka funkcja] ewentualnie + &player=[index] lub &result=[true/false])
@app.route("/test", methods=['GET'])
def test():
    match request.args["func"]:
        case "start":
            startGame()
        case "who":
            whoAnswering(int(request.args["player"]))
        case "result":
            answerResult(request.args["result"])
        case "table":
            pointsTable()
    return "Done!"


if __name__ == "__main__":

    background_process = Process(target=background_task, args=(shared_answerResult,))
    background_process.start()

    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)

    background_process.join()

    print("Closed correctly!")