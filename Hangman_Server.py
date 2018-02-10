#!/usr/bin/python

import  socket                                  # for sockets
import  sys                                     # for exit
import  thread                                  # for start_new_thread
import  psycopg2                                # for postgresql

from socket import timeout
import select
import random

# ---------- Setting HOST and PORT
HOST = ''   # Symbolic name meaning all available interfaces
PORT = 8888 # Arbitrary non-privileged port

# ---------- Create Socket
try:
    # create an AF_INET, STREAM socket (TCP)
    # socket(family, type[,protocal])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

except socket.error, msg:   # error will pass to msg
    print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
    sys.exit()
 
print 'Socket Created'

# ---------- Bind the socket to local host and PORT
try:
    # Function bind can be used to bind a socket to a particular address and port.
    s.bind((HOST, PORT))

except socket.error , msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()
     
print 'Socket bind complete'
 
# ---------- Start listening on socket
# ---------- s.listen(backlog)
# ---------- backlog means 
s.listen(10)
print 'Socket now listening'

connection_list = []

# [player 1 id, player 2 id, ...]
online_player_id_list = []
# {player_id : [conn, user name, score], player_id : [conn, user name, score], ...}
online_list = {}
# {game id : [Question, Answer, Incorrect, current player index, player 1 id, player 2 id, player 3 id], ...}
games_list = {}

# Client Thread
def clientthread(conn, addr):
    database_connection = psycopg2.connect(database="hangman_game", user="lengzhang", password="", host="127.0.0.1", port="7432")
    cursor = database_connection.cursor()

    # --------------------------------------------------
    # Print Hall of Fame
    def Hall_of_Fame():
        cursor.execute("select username, score from players order by score desc;")
        rows = cursor.fetchall()
        # Check the list is empty or not
        if len(rows) == 0:
            conn.sendall('\n\tNo one played this game T_T\n')
            return
        # Print list
        msg = '\n\t\tHall of Fame\n\t'
        while len(msg) < 44:
            msg = msg + '-'
        msg = msg + '\n'
        conn.sendall(msg)
        for row in rows:
            us_name = row[0]
            while len(us_name) < 21:
                us_name = us_name + ' '
            conn.sendall('\t' + us_name + '\t' + str(row[1]) + '\n')
        database_connection.commit()

    # Get random word but w (word)
    def get_random_word(w):
        cursor.execute('select word from words;')
        rows = cursor.fetchall()
        # Check the list is empty or not
        if len(rows) == 0:
            return ""
        if (w,) in rows:
            rows.remove((w,))
        return rows[random.randint(0, len(rows) - 1)][0]

    # Initial answer for w(word)
    def generate_player_list(gid):
        result = ""
        for i in range(4, len(games_list[gid])):
            result += "\t"
            temp = ""
            if i == (3 - games_list[gid][3]):
                temp += "* "
            else:
                temp += "  "
            temp += online_list[games_list[gid][i]][1]
            while len(temp) < 23:
                temp += " "
            temp += str(online_list[games_list[gid][i]][2]) + "\n"
            result += temp
        return result

    # Check answer by msg (input)
    def check_answer(gid, msg):
        # Answer whole word
        if len(msg) == len(games_list[gid][1]):
            if msg == games_list[gid][1]:
                games_list[gid][0] = games_list[gid][1]
                return len(games_list[gid][1])
            else:
                return 0
        # Answer one letter
        elif len(msg) == 1:
            points = 0
            for i in range(0, len(games_list[gid][1])):
                if msg == games_list[gid][1][i] and games_list[gid][0][i] == "_":
                    points += 1
                    games_list[gid][0] = games_list[gid][0][:i] + msg + games_list[gid][0][i+1:]

            if points == 0 and games_list[gid][2].find(msg) == -1:
                games_list[gid][2] += msg
            return points
        # 1 < len(msg) < len(games_list[gid][1]) or len(msg) > len(games_list[gid][1])
        else:
            return 0
    # --------------------------------------------------
    # players (player_id, username, password, score)
    # words (word_id, word)
    #Sending message to connected client
    conn.sendall('\nWelcome to the Hangman Game by Leng Zhang\n') #send only takes string
    global connection_list
    #infinite loop so that function do not terminate and thread do not end.
    while True:
        # Player Menu:
        #   1. Login
        #   2. Make New User
        #   3. Hall of Fame
        #   4. Exit
        # Please enter your choice: 
        conn.sendall('\nPlayer Menu:\n\t1. Login\n\t2. Make New User\n\t3. Hall of Fame\n\t4. Exit\nPlease enter your choice: ')
        #Receiving from client
        data = conn.recv(1024)
        choice = data[:-2]
        
        # 1. Login
        if choice == '1':
            state = 0
            user_info = []  # [player_id, username, password, score]
            while True:
                # Check User Name
                if state == 0:
                    #   What is Your User Name?
                    conn.sendall('\nPlayer Menu -> Login\nPlease enter your User Name: ')
                    data = conn.recv(1024)
                    user_name = data[:-2]
                    # Check User Name
                    if user_name == '':
                        state = -1
                        continue
                    # Check does the new User Name exist in the list
                    cursor.execute('select * from players where username = %s;', (user_name,))
                    rows = cursor.fetchall()
                    if len(rows) == 0:
                        conn.sendall('\n\tError: This User Name does not existed!\n')
                        continue
                    elif rows[0][0] in online_player_id_list:
                        conn.sendall('\n\tError: This User Name is online!\n')
                        state = -1
                        continue
                    else:
                        for i in rows[0]:
                            user_info.append(i)
                        state = 1
                        continue

                # Check Password
                elif state == 1:
                    #   What is Your Password?
                    pw_counter = 0
                    while pw_counter < 3:
                        conn.sendall('\nPlayer Menu -> Login\nPlease enter your Password: ')
                        data = conn.recv(1024)
                        password = data[:-2]
                        # Empty exit
                        if password == '':
                            pw_counter = 4
                            break
                        # correct 
                        elif password == user_info[2]:
                            break
                        # incorrect try 3 times
                        else:
                            pw_counter += 1

                    # correct
                    if pw_counter < 3:
                        online_player_id_list.append(user_info[0])
                        online_list[user_info[0]] = [conn, user_info[1], user_info[3]]
                        state = 2
                    # exit
                    else:
                        state = -1

                # Player Menu -> Login
                #   1. Start New Game
                #   2. Get list of the Games
                #   3. Hall of Fame
                #   4. Exit
                # Please enter your choice: 
                elif state == 2:
                    conn.sendall('\nPlayer -> ' + user_info[1] + '\n\t1. Start New Game\n\t2. Get list of the Games\n\t3. Hall of Fame\n\t4. Exit\nPlease enter your choice: ')
                    #Receiving from client
                    data = conn.recv(1024)
                    inner_choice = data[:-2]
                    if inner_choice == '1':
                        state = 3
                    elif inner_choice == '2':
                        state = 4
                    elif inner_choice == '3':
                        state = 5
                    elif inner_choice == '4':
                        state = -1
                    # input invalid
                    else:
                        conn.sendall("\n\tError: Your input is invalid!\n")
                        continue

                #   1. Start New Game
                elif state == 3:
                    # Get Difficulty
                    game_life = 4
                    while True:
                        conn.sendall('\nPlayer -> ' + user_info[1] + '\nChoose the difficulty:\n\t1. Easy\n\t2. Medium\n\t3. Hard\nPlease enter your choice: ')
                        #Receiving from client
                        data = conn.recv(1024)
                        diff_choice = data[:-2]
                        # Easy Medium Hard
                        if diff_choice == '1' or diff_choice == '2' or diff_choice == '3':
                            game_life = game_life - int(diff_choice)
                            break
                        # input invalid
                        else:
                            conn.sendall("\n\tError: Your input is invalid!\n")
                            continue
                    # Geting available game_id
                    game_id = -1
                    # Check is any game not ful
                    for key, value in games_list.items():
                        if len(value) < 7:
                            game_id = key
                            break
                    # Get available game_id
                    if game_id == -1:   # all games are full, create new game
                        game_id = 0
                        while games_list.has_key(game_id):
                            game_id += 1
                        games_list[game_id] = ["", "", "", -1, user_info[0]]
                    else:               # game_id is not full, add to game
                        games_list[game_id].append(user_info[0])
                        
                    # Gaming
                    online_list[user_info[0]][2] = 0
                    game_state = 0
                    # [question, incorrect, player index]
                    # previous = [["", "", -1]]
                    previous = ["", "", "", -1]
                    update = 0
                    while True:
                        # 0 - Just get In
                        if game_state == 0:
                            if games_list[game_id][0] == games_list[game_id][1]:
                                games_list[game_id][2] = ""
                                games_list[game_id][1] = get_random_word(games_list[game_id][1])
                                games_list[game_id][0] = ""
                                for i in range(0, len(games_list[game_id][1])):
                                    games_list[game_id][0] += "_"

                            #if previous[0] != games_list[game_id][0] or previous[1] != games_list[game_id][2] or previous[2] != games_list[game_id][3]:
                            if cmp(previous, games_list[game_id]) != 0 or update == 1:
                                update = 0
                                msg = "\nGame " + str(game_id)
                                msg += " -> " + user_info[1]
                                msg += " " + str(game_life) + " chance(s)\n"
                                msg += "\t" + games_list[game_id][0] + "\n\t" + games_list[game_id][2]
                                msg += "\n" + generate_player_list(game_id)
                                msg += "\nAnswer:\t"
                                conn.sendall(msg)
                                previous = games_list[game_id][:]

                            if games_list[game_id][3-games_list[game_id][3]] == user_info[0]:
                                game_state = 1
                            else:
                                game_state = 2

                        # Current Gamer
                        elif game_state == 1:
                            conn.settimeout(0.5)
                            try:
                                data = conn.recv(1024)
                                conn.settimeout(None)
                                if len(data[:-2]) == 0:
                                    game_state = 0
                                    update = 1
                                    continue
                                points = check_answer(game_id, data[:-2].lower())
                                if points > 0:
                                    online_list[user_info[0]][2] += points
                                    game_state = 0
                                else:
                                    game_state = 3

                            except socket.timeout:
                                game_state = 0
                                conn.settimeout(None)

                        # Waiting Gamer
                        elif game_state == 2:
                            conn.settimeout(0.5)
                            try:
                                data = conn.recv(1024)
                                conn.settimeout(None)
                                if len(data[:-2]) == 0:
                                    game_state = 0
                                    update = 1
                                    continue
                                ans = data[:-2].lower()
                                if ans == games_list[game_id][1]:
                                    online_list[user_info[0]][2] += check_answer(game_id, ans)
                                else:
                                    game_state = -1
                                    continue

                            except socket.timeout:
                                conn.settimeout(None)

                            game_state = 0

                        # Move to next
                        elif game_state == 3:
                            update = 1
                            game_life -= 1
                            if 3 - games_list[game_id][3] == len(games_list[game_id]) - 1:
                                games_list[game_id][3] = -1
                            else:
                                games_list[game_id][3] -= 1

                            if game_life == 0:
                                game_state = -1
                            else:
                                game_state = 0
                        else:
                            conn.sendall("\n\tGame Over!\n")
                            if games_list[game_id].index(user_info[0]) <= 3 - games_list[game_id][3]:
                                games_list[game_id][3] += 1


                            games_list[game_id].remove(user_info[0])
                            #if 3 - games_list[game_id][3] > len(games_list[game_id]) - 1:
                            #   games_list[game_id][3] = len(games_list[game_id]) - 1
                            if len(games_list[game_id]) < 5:
                                del games_list[game_id]

                            # Update Score to Database
                            cursor.execute("update players set score = %s where player_id = %s;", (str(online_list[user_info[0]][2]), str(user_info[0])))
                            database_connection.commit()

                            break
                    state = 2

                #   2. Get list of the Games
                elif state == 4:
                    # {game id : [Question, Answer, Incorrect, current player index, player 1 id, player 2 id, player 3 id, player 4 id], ...}
                    if len(games_list) == 0:
                        conn.sendall("\n\tNo Game!\n")
                    else:
                        for key, value in games_list.items():
                            msg = "\nGame " + str(key)
                            msg += "\nPlayers:\n"
                            for i in range(4, len(value)):
                                msg += "\t" + online_list[value[i]][1] + "\n"
                            conn.sendall(msg)
                    state = 2
                #   3. Hall of Fame
                elif state == 5:
                    Hall_of_Fame()
                    state = 2
                # Logout
                else:
                    if len(user_info):
                        if online_player_id_list.count(user_info[0]) > 0:
                            online_player_id_list.remove(user_info[0])
                        if online_list.has_key(user_info[0]):
                            del online_list[user_info[0]]
                        while len(user_info):
                            user_info.pop()
                    break
            continue

        # 2. Make New User
        elif choice == '2':
            state = 0
            new_un = ''
            new_pw = ''
            while True:
                # User Name
                if state == 0:
                    #   What is Your User Name?
                    conn.sendall('\nPlayer Menu -> Make New User\nPlease enter your User Name: ')
                    data = conn.recv(1024)
                    new_un = data[:-2]
                    new_un = new_un.lower()
                    # Check User Name
                    if new_un == '':
                        state = -1
                        continue
                    if len(new_un) > 15:
                        conn.sendall('\n\tError: This User Name is too long!\n')
                        continue
                    # Check does the new User Name exist in the list
                    cursor.execute('select username from players where username = %s;', (new_un,))
                    rows = cursor.fetchall()
                    if len(rows) != 0:
                        conn.sendall('\n\tError: This User Name existed!\n')
                        continue
                    else:
                        state = 1
                        continue
                # Password
                elif state == 1:
                    #   What is Your Password?
                    conn.sendall('\nPlayer Menu -> Make New User\nPlease enter your Password: ')
                    data = conn.recv(1024)
                    new_pw = data[:-2]
                    if new_pw == '':
                        continue
                    elif len(new_pw) > 15:
                        conn.sendall('\n\tError: This Password is too long!\n')
                        continue
                    else:
                        state = 2
                        continue
                # Check player_id
                elif state == 2:
                    # Check the next available player_id
                    next_player_id = 0
                    while True:
                        cursor.execute("select player_id from players where player_id = %s;", (str(next_player_id)))
                        rows = cursor.fetchall()
                        if len(rows) == 0:
                            break
                        next_player_id += 1
                    # Insert new data
                    cursor.execute("INSERT INTO players (player_id, username, password, score) VALUES (%s, %s, %s, %s);", (str(next_player_id), new_un, new_pw, str(0)))
                    database_connection.commit()
                    conn.sendall('\n\tCreating new user is successful!\n')
                    state = -1
                    continue
                else:
                    break

        # 3. Hall of Fame
        elif choice == '3':
            Hall_of_Fame()
            continue

        # 4. Exit
        elif choice == '4':
            conn.sendall("Connection is closing...\n")
            conn.close()
            connection_list.remove(conn)
            break

        # input invalid
        else:
            conn.sendall("\n\tError: Your input is invalid!\n")
            continue

    database_connection.close()

# Server Thread
def serverthread():
    print '\nWelcome to Hangman Game Server'
    database_connection = psycopg2.connect(database="hangman_game", user="lengzhang", password="", host="127.0.0.1", port="7432")
    cursor = database_connection.cursor()
    # players (player_id, username, password, score)
    # words (word_id, word)
    while True:
        # Server Menu:
        #   1. Current list of the users
        #   2. Current list of the words
        #   3. Add new word to the list of words
        # Please enter your choice: 
        choice = raw_input('\nServer Menu:\n\t1. Current list of the users\n\t2. Current list of the words\n\t3. Add new word to the list of words\n\t4. Debuging\nPlease enter your choice: ')
        
        #   1. Current list of the users
        if choice == '1':
            cursor.execute('select * from players order by player_id asc;')
            rows = cursor.fetchall()
            # Check the list is empty or not
            if len(rows) == 0:
                print '\nPlayer list is empty'
                continue
            # Print list
            print '\nList of players:'
            for row in rows:
                temp_un = ""
                for i in range(0, 20):
                    if i < len(row[1]):
                        temp_un += row[1][i]
                    else:
                        temp_un += " "
                print '\tid = ' + str(row[0]) + '\tusername = ' + temp_un + '\tscore = ' + str(row[3])

        #   2. Current list of the words
        elif choice == '2':
            cursor.execute('select * from words;')
            rows = cursor.fetchall()
            # Check the list is empty or not
            if len(rows) == 0:
                print '\nWord list is empty'
                continue
            # Print list
            print '\nList of words:'
            for row in rows:
                print '\t' + str(row[0]) + '\t' + row[1]

        #   3. Add new word to the list of words
        elif choice == '3':
            # Get the new word
            word = raw_input('\nServer Menu -> Add new word to the list of words\nPlease enter the NEW word: ')
            word = word.lower()
            if word.find(" ") != -1:
                print '\n\tError: The new word included contained space!'
                continue
            if word == '':
                continue
            # Check does the new word exist in the list
            cursor.execute('select word from words where word = %s;', (word,))
            rows = cursor.fetchall()
            if len(rows) != 0:
                print '\n\tError: The new word existed!'
                continue
            # Check the next available word_id
            next_word_id = 0
            while True:
                cursor.execute("select word_id from words where word_id = %s;", (str(next_word_id)))
                rows = cursor.fetchall()
                if len(rows) == 0:
                    break
                next_word_id += 1
            # Insert new data
            cursor.execute("INSERT INTO words (word_id, word) VALUES (%s, %s);", (str(next_word_id), word))
            database_connection.commit()

        #   4. debuging print all list
        elif choice == '4':
            # [player 1 id, player 2 id, ...]
            print '\nonline_player_id_list = ' + str(online_player_id_list)
            # {(player_id : [conn, user name, score], ...}
            print '\nonline_list = ' + str(online_list)
            # {game id : [current player index, player 1 id, player 2 id, player 3 id, player 4 id], ...}
            print '\ngames_list = ' + str(games_list)
        # input invalid
        else:
            print '\n\tError: Your input is invalid!'
            continue
    
    database_connection.close()

thread.start_new_thread(serverthread, ())

#now keep talking with the client
while True:
    #wait to accept a connection - blocking call
    conn, addr = s.accept()
    #start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
    thread.start_new_thread(clientthread ,(conn, addr))
    connection_list.append(conn)

s.close()
sys.exit()