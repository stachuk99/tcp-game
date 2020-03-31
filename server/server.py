import socket
import random
import threading
import time
from queue import Queue


class Server:
    def __init__(self):
        self.X = random.randrange(65536)  # wygenerowanie szukanej liczby
        print("Number to guess: " + str(self.X))
        self.id_list = [random.randrange(32), random.randrange(32)] # wygenerowanie ID
        while self.id_list[0] == self.id_list[1]:  # zapewnienie żeby ID były różne
            self.id_list[1] = random.randrange(32)
        self.OperationID = 1
        self.AnswerID = 0
        self.Data = 0
        self.SessionID = 0
        self.GameTime = (abs(self.id_list[0] - self.id_list[1])*74) % 90 + 25
        # maksymalny czas trwania sesji
        self.Time = 0  # czas trwania sesji
        self.is_running = True
        self.connections_list = []
        self.threads_list = []
        self.addresses_list = []
        self.host = socket.gethostname()
        self.port = 5001
        self.socket = socket.socket() # utworzenie obiektu gniazda
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True) # wyłączenie algorytmu Nagle'a
        self.queue = Queue()

    def run(self):  # główna funkcja w której dzieje się wszystko
        print("Server ran")
        self.init_connection()
        self.init_threads()
        self.set_id()
        while self.is_running:
            try:
                if self.Time >= self.GameTime:
                    #  self.is_running = False
                    for i, conn in enumerate(self.connections_list):
                        conn.send(self.to_bytearray(
                            self.id_list[i], 7, 0, 0))
                elif self.Time % 15 == 2:
                    for i, conn in enumerate(self.connections_list):
                        time_left = int(self.GameTime - self.Time)
                        conn.send(self.to_bytearray(self.id_list[i], 3, 0, time_left))
                print("Remaining time: " + str(self.GameTime - self.Time))
                self.Time += 1
                time.sleep(1)
                if self.connections_list.__len__() == 0:
                    break
            except Exception as er:
                break
        time.sleep(2)
        self.close_threads()
        # self.socket.close()
        print("server is closed")

    def init_connection(self):  # oczekiwanie na połączenia
        try:
            self.socket.bind((self.host, self.port))  # przypisanie gniazda do portu
            self.socket.listen(2)  # ograniczenie do dwóch połączeń
            self.socket.setblocking(True)
        except socket.error as er:
            if self.socket:
                self.socket.close()
            print("Could not open the socket: " + format(er.args))
        while len(self.connections_list) < 2:
            try:
                conn, address = self.socket.accept()    # przypisanie połączenia do zmiennej
                print("Connection from: " + str(address))
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)    # wyłączenie algorytmu Nagle'a
                self.connections_list.append(conn)  # dodanie połączenia do listy
                self.addresses_list.append(address)
                data = conn.recv(4)  # oczekiwanie na prośbę o nadaie ID
                self.to_client(data)
                if not self.SessionID == 0:
                    print("ID not assigned")
                    self.is_running = False
            except socket.error as er:
                print("Client not available")

    def set_id(self):  # nadanie ID clientom i start rozgrywki
        for i, conn in enumerate(self.connections_list):
            conn.send(self.to_bytearray(self.id_list[i], 1, 4, 0))
            conn.send(self.to_bytearray(self.id_list[i], 2, 0, 0))

    def init_threads(self):  # uruchomienie wątków
        self.threads_list.append(threading.Thread(target=self.interpreting, args=(), daemon=True))
        for conn in self.connections_list:
            self.threads_list.append(threading.Thread(target=self.receiving, args=(conn,),  daemon=True))
        for t in self.threads_list:
            t.start()

    def interpreting(self):  # interpretacja otrzymanych wiadomości oraz wysyłanie odpowiedzi
        while self.is_running:
            if not self.queue.empty():
                data = self.queue.get()  # wzięcie kolejnej wiadomości z kolejki
                self.to_client(data)
                print("Client: " + str(self.SessionID) + " send " + str(self.Data))
                if self.id_list.__len__() > 1:
                    if self.SessionID == self.id_list[0]:
                        conn = self.connections_list[0]
                        i = 1
                    elif self.SessionID == self.id_list[1]:
                        conn = self.connections_list[1]
                        i = 0
                    else:
                        print("Incorrect ID")
                        break
                    if self.Data == self.X:  # sprawdzenie czy wartość została odgadnięta
                        print("Client: " + str(self.SessionID) + " Won the game")
                        conn.send(self.to_bytearray(
                            self.SessionID, 4, 7, 0))  # wysłanie komunikatów o wygranej i końcu gry
                        conn.send(self.to_bytearray(
                            self.SessionID, 7, 4, 0))
                        if self.id_list.__len__() > 1:
                            self.connections_list[i].send(self.to_bytearray(
                                self.id_list[i], 7, 7, 0)) # wysłanie komunikatu o przegranej do drugiego klienta
                    else:
                        conn.send(self.to_bytearray(
                            self.SessionID, 4, 4, 0)) # wysłąnie komunikatu o tym że nie zgadanięto
            else:
                time.sleep(0.1)

    def receiving(self, conn):  # nasłuwichanie wiadomości i dodanie ich do kolejki oczekującej na interpretacje
        while self.is_running:
            try:
                data = conn.recv(4)  # nasłuchwiwanie na wiadomości
                if data:
                    self.queue.put(data)    # dodanie wiadomości do kolejki
            except socket.error as er:
                print("Connection with client is closed")
                self.is_running = False

    def to_client(self, mess):  # dekodowanie wiadomości i przypisanie wiadomości do pól obiektu
        #  serwera odpowiadających konkretnym fragment komunikatu
        self.OperationID = mess[0] // 32
        self.AnswerID = (mess[0] // 4) % 8
        self.SessionID = (mess[0] % 4) * 8 + mess[1] // 32
        self.Data = (mess[1] % 32) * 2048 + mess[2] * 8 + mess[3] // 32

    def to_bytearray(self, session_id, operation_id, answer_id, data):  # koduje wiadomość
        mess = bytearray()
        mess.append(operation_id * 32 + answer_id * 4 + session_id // 8)
        mess.append((session_id % 8) * 32 + data // 2048)
        mess.append((data % 2048) // 8)
        mess.append((data % 8) * 32)
        return mess

    def close_threads(self):  # zamknięcie działających wątków
        for t in self.threads_list:
            t.run = False


if __name__ == '__main__':
    server = Server()
    server.run()

