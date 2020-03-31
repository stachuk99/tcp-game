import socket
import random
import time
import threading
from queue import Queue


class Client:
    def __init__(self):
        self.OperationID = 1
        # możliwe ID                           # odpowiedzi serwera
        # { 0-
        #   1- nadanie ID                      4- nadano            7- błąd
        #   2- start rozgrywki
        #   3- informacja o czasie             0- pozostały czas
        #   4- próba zgadnięcia                4- nie zgadnięto      7- zgadnięto
        #   5-
        #   6-
        #   7-koniec rozgrywki                 0-koniec czasu,     4-wygrana   7- przegrana }
        self.SessionID = 0
        self.AnswerID = 0
        self.Data = 0
        self.is_running = True
        self.host = socket.gethostname()
        self.port = 5001
        self.socket = socket.socket() # utworzenie obiektu gniazda
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)  # wyłączenie algorytmu Nagle'a
        self.queue = Queue()
        self.x = -1

    def run(self):
        print("Client ran")
        self.init_connection()  # nawiązanie połączenia i nadanie ID
        self.init_threads()     # włączenie wątków do wysyłania i nasłuchiwania
        while self.is_running:
            time.sleep(0.1)
        self.close_threads()  # zamknięcie działających wątków
        self.socket.close()  # zakończenie połączenia
        print("Aplication is closed")

    def init_connection(self):
        try:
            self.host = input("Type server IP->")
            self.port = input("Type server port->")
            self.socket.connect((self.host, int(self.port)))  # nawiązanie połączenia TCP
        except Exception as er:
            print("Connection error, try again")
            self.init_connection()
            return
        print("Connected")
        self.socket.send(self.to_bytearray(1, 0, 0)) # wysłanie prośby o ID
        data = self.socket.recv(4)  # Odpowiedź z ID
        self.to_client(data)
        if self.OperationID == 1 and self.AnswerID == 4:
            self.SessionID = (data[0] % 4) * 8  # przypisanie ID
            self.SessionID += data[1] // 32
            print("ID assigned: " + str(self.SessionID))
            return 1
        elif self.OperationID == 1 and self.AnswerID == 7:
            print("ID assignement error")
            return 0
        else:
            print("ID not assigned")
            return 0

    def init_threads(self):
        self.send = threading.Thread(target=self.sending, daemon=True)
        self.receiv = threading.Thread(target=self.receiving, daemon=True)
        self.inter = threading.Thread(target=self.interpreting, daemon=True)
        self.receiv.start()
        self.inter.start()

    def to_bytearray(self, operation_id, answer, data):  # koduje wiadomość
        mess = bytearray()
        mess.append(operation_id * 32 + answer*4 + self.SessionID // 8)
        mess.append((self.SessionID % 8) * 32 + data // 2048)
        mess.append((data % 2048) // 8)
        mess.append((data % 8) * 32)
        return mess

    def to_client(self, mess):  # dekoduje wiadomość
        self.OperationID = mess[0] // 32
        self.AnswerID = (mess[0] // 4) % 8
        self.Data = (mess[1] % 32) * 2048 + mess[2] * 8 + mess[3] // 32

    def interpreting(self):  # interpretacja otrzymanych wiadomości
        while self.is_running:
            if not self.queue.empty():
                data = self.queue.get()  # pobranie kolejnej wiadomości z kolejki
                self.to_client(data)
                if self.OperationID == 3:
                    if self.AnswerID == 0:  # 0- pozostały czas
                        print("Remaining time: " + str(self.Data))
                elif self.OperationID == 2:
                    print("Game start")
                    self.send.start()
                elif self.OperationID == 4:  # 4- nie zgadnięto      7- zgadnięto
                    if self.AnswerID == 4:
                        print("Wrong answer, try again")
                    if self.AnswerID == 7:
                        print("Congratulation you quessed")
                elif self.OperationID == 7:
                    if self.AnswerID == 0:  # 0-koniec czasu,     4-wygrana   7- przegrana }
                        print("You lose due to end of time")
                        print("Listening stop, press enter button to close the application")
                    elif self.AnswerID == 4:
                        print("You won !!!")
                    elif self.AnswerID == 7:
                        print("Game is lost, another client won")
                        print("Listening stop, press enter to close the application")
                    self.is_running = False
                    self.socket.close()
                elif self.OperationID == 1:
                    print("ID already assigned!")
            else:
                time.sleep(0.1)

    def receiving(self):  # nasłuchiwanie na wiadomości i dodanie ich do kolejki
        print("listening")
        while self.is_running:
            try:
                data = self.socket.recv(4)  # odbieranie odpowiedzi
                if data:
                    self.queue.put(data)    # dodanie wiadomości do kolejki
            except socket.error as er:
                # print("Receiving error " + str(er.args))
                print("Connection with server is closed")
                self.is_running = False
        return

    def sending(self):  # zgadywanie liczby i przesyłanie do serwera
        while self.is_running:
            try:
                self.x = int(input("Type integer value ->"))  # wczytanie liczby z klawiatury
                if 0 <= self.x < 65536:
                    try:
                        self.socket.send(self.to_bytearray(4, 0, self.x))  # przesłanie zgadywanej liczby
                    except socket.error as er:
                        print("sending error " + str(er.args))
                        self.socket.close()
                        self.is_running = False
                else:
                    print("Type positive number smaller than 65 535")
            except ValueError as er:
                if self.is_running:
                    print("It's not a integer, try again")
            time.sleep(0.5)

    def close_threads(self):
        if self.receiv:
            self.receiv.run = False
            self.send.run = False
            self.receiv.join()
            self.send.join()


if __name__ == '__main__':
    client = Client()  # utworzenie obiektu klienta
    client.run()




