from flask import Flask, request, render_template
from flask_socketio import SocketIO
from json import loads
from random import shuffle
from multiprocessing import Process,Value

class Questions:

    def __init__(self):
        with open("./Static/questions.json", 'r') as f:
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
questions = Questions()
players = [
    {
        "name":"Test",
        "points":0
    }
]

#Zmienne które działają z procesem seriala
shared_answerResult = Value('i',-1)

#Funkcja która działa jako proces w tle
def background_task(shared_answerResult):
    with shared_answerResult.get_lock():
        shared_answerResult.value = -1

#Funkcje które działają na stronie (można ich używać w bacground_task)
def startGame():
    global questions
    questions.next()
    shared_answerResult.value = -1
    data = {"question":questions.value,"html":"TODO"}
    io.emit("start",f'{data}')

def whoAnswering(index:int):
    data = {"player":players[index]}
    io.emit("answering",f'{data}')

def answerResult(result:bool):
    shared_answerResult.value = int(result)
    io.emit("result",result)

def pointsTable():
    data = {"players":players,"html":"TODO"}
    io.emit("table",f'{data}')

#Routy dla weba
@app.route("/")
def index():
    return render_template("index.html")

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