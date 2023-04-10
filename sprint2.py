# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import null
from waitress import serve
from flask_socketio import SocketIO, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, \
    logout_user, current_user, login_required
import random




app = Flask(__name__, static_url_path='/static')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blackjack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "secret"
socketio = SocketIO(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.init_app(app)


class Card(db.Model):
    card_id = db.Column('card_id', db.Integer, primary_key = True)
    symbol = db.Column(db.String(100))
    suit = db.Column(db.String(100))
    value = db.Column(db.Integer)
    dealt = db.Column(db.Integer)
    image = db.Column(db.String(100))
    back = db.Column(db.String(100))


class User(UserMixin, db.Model):
    id = db.Column('user_id', db.Integer, primary_key = True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    bet = db.Column(db.Integer)
    cash = db.Column(db.Integer)
    handid = db.Column(db.Integer)
    splitHand = db.Column(db.Integer)
    playing = db.Column(db.Integer)
    personBet = db.Column(db.Integer)
    session = db.Column(db.String(100))
    bust = db.Column(db.Integer)


class Hands(db.Model):
    hand_id = db.Column('hand_id', db.Integer, primary_key = True)
    dealerId = db.Column(db.Integer)
    userId = db.Column(db.Integer)
    cardOne = db.Column(db.Integer)
    cardTwo = db.Column(db.Integer)
    cardThree = db.Column(db.Integer)
    cardFour = db.Column(db.Integer)
    cardFive = db.Column(db.Integer)
    value = db.Column(db.Integer)

user = User()

@login_manager.user_loader
def load_user(uid):
    global user
    user = User.query.get(uid)
    return user

'''
symbol = [2, 3, 4, 5, 6, 7, 8, 9, 10, "jack", "queen", "king", "ace"]


suit = ["spades", "diamonds", "hearts", "clubs"]

deck = []
for i in range(0,3):
    for v in symbol:
        for s in suit:
            deck.append(str(v) + " of " + s)
random.shuffle(deck)
'''

def getVal(symbol):
    if symbol == "jack" or symbol == "queen" or symbol == "king":
        value = 10
    elif  symbol == "ace":
        value = 11
    else:
        value=int(symbol)
    return int(value)

def getCard():
    c = db.session.execute('SELECT * FROM Card WHERE dealt = 0 ORDER BY RANDOM() LIMIT 1')
    print("c:")
    for row in c:
        c_id = row["card_id"]
        print(c_id)
    return c_id

def deal(players):
    global dealt
    print("dealing")
    for player in players:
        c_id = getCard()
        #currentCard = deck.pop()
        #cardSplit = currentCard.split(" of ")
        #val = cardSplit[0]
        #symbol = cardSplit[1]
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        hand = Hands()
        hand.cardOne = card.card_id
        total = card.value

        #currentCard2 = deck.pop()
        #cardSplit = currentCard2.split(" of ")
        #val = cardSplit[0]
        #symbol = cardSplit[1]
        c_id = getCard()
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        hand.cardTwo = card.card_id
        total+= card.value

        hand.userId = player.id
        hand.value= total;
        db.session.add(hand)
        db.session.commit()
        User.query.filter_by(id=player.id).update({'handid':hand.hand_id})
        db.session.commit()
    hand = Hands()
    c_id = getCard()
    #currentCard = deck.pop()
    #cardSplit = currentCard.split(" of ")
    #val = cardSplit[0]
    #symbol = cardSplit[1]
    card = Card.query.filter_by(card_id = c_id).first()
    card.dealt = 1
    hand.cardOne = card.card_id
    dealerTotal = card.value
    
    c_id = getCard()
    #currentCard2 = deck.pop()
    #cardSplit = currentCard2.split(" of ")
    #val = cardSplit[0]
    #symbol = cardSplit[1]
    card = Card.query.filter_by(card_id = c_id).first()
    card.dealt = 1
    hand.cardTwo = card.card_id
    dealerTotal += card.value
    hand.dealerId = 1;
    hand.value = dealerTotal
    db.session.add(hand)
    db.session.commit()
    dealt = True

def getSessionsPlaying():
    playing =  User.query.filter_by(playing=1)
    sessions = []
    for player in playing:
        if player.bust != 1:
            sessions.append(player.session)
    return sessions

connected = 0
reloadFirstDeal = False
dealt = False
index = 0
dl = False

@app.route('/', methods=['GET','POST'])
def home():
    global user
    a= False
    b = True ##needs login form
    if request.method == "POST":
        button = request.form['buttonType']
        if button == 'loginForm':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user != None:
                if password == user.password:
                    print("hey")
                    login_user(user)
                    print("here")
                    a = True #if login successful
                    b = False #no longer needs login form
            return render_template('home.html', a=a, b=b)
        else:
            return redirect('/game')
    return render_template('home.html', a=a, b=b)

@app.route('/game', methods=['GET','POST'])
@login_required
def game():
    #set playing to true
    global user
    global reloadFirstDeal
    global dealt
    global index
    global dl
    betting = True
    if request.method == "POST":
        userid = current_user.id
        user = User.query.filter_by(id=userid).first()
        User.query.filter_by(id=userid).update({'personBet':1})
        userBet = request.form['bet']
        User.query.filter_by(id=userid).update({'bet':userBet})

        db.session.commit()
        numberPlaying = User.query.filter_by(playing=1).count()
        numberBet = User.query.filter_by(personBet=1).count()
        if (numberPlaying == numberBet):
            if (reloadFirstDeal == False and dealt == False):
                print("ready to deal")
                playing =  User.query.filter_by(playing=1)
                deal(playing)
                socketio.emit("reload")


            betting = False
            yourHands = []
            yourHand = []
            sHand = []
            user = User.query.filter_by(id=current_user.id).first()
            Hand = Hands.query.filter_by(hand_id= user.handid).first()
            card = Card.query.filter_by(card_id = Hand.cardOne).first()
            yourHand.append(card.image)
            card = Card.query.filter_by(card_id = Hand.cardTwo).first()
            yourHand.append(card.image)
            card = Card.query.filter_by(card_id = Hand.cardThree).first()
            if card != None:
                yourHand.append(card.image)
            card = Card.query.filter_by(card_id = Hand.cardFour).first()
            if card != None:
                yourHand.append(card.image)
            card = Card.query.filter_by(card_id = Hand.cardFive).first()
            if card != None:
                yourHand.append(card.image)
            yourHands.append(yourHand)
            if user.splitHand != None:
                userSplitHand = Hands.query.filter_by(hand_id= user.splitHand).first()
                card = Card.query.filter_by(card_id = userSplitHand.cardOne).first()
                sHand.append(card.image)
                card = Card.query.filter_by(card_id = userSplitHand.cardTwo).first()
                sHand.append(card.image)
                card = Card.query.filter_by(card_id = userSplitHand.cardThree).first()
                if card != None:
                    sHand.append(card.image)
                card = Card.query.filter_by(card_id = userSplitHand.cardFour).first()
                if card != None:
                    sHand.append(card.image)
                card = Card.query.filter_by(card_id = userSplitHand.cardFive).first()
                if card != None:
                    sHand.append(card.image)
                yourHands.append(sHand)

            dealers = []
            dealer = Hands.query.filter_by(dealerId = 1).first()
            card = Card.query.filter_by(card_id = dealer.cardOne).first()
            dealers.append(card.image)
            card = Card.query.filter_by(card_id = dealer.cardTwo).first()
            dealers.append(card.back)

            others = []
            cards = []
            scards=[]
            playing =  User.query.filter_by(playing=1)
            for player in playing:
                if(player.id != current_user.id):
                    hand =  Hands.query.filter_by(hand_id= player.handid).first()
                    card = Card.query.filter_by(card_id = hand.cardOne).first()
                    card2 = Card.query.filter_by(card_id = hand.cardTwo).first()
                    cards.append(card.image)
                    cards.append(card2.image)
                    card = Card.query.filter_by(card_id = hand.cardThree).first()
                    if card != None:
                        cards.append(card.image)
                    card = Card.query.filter_by(card_id = hand.cardFour).first()
                    if card != None:
                        cards.append(card.image)
                    card = Card.query.filter_by(card_id = hand.cardFive).first()
                    if card != None:
                        cards.append(card.image)
                    cardsCopy = cards.copy()
                    others.append(cardsCopy)
                    cards.clear()
                    
                    if player.splitHand != None:
                        splitOffHand = Hands.query.filter_by(hand_id= player.splitHand).first()
                        card = Card.query.filter_by(card_id = splitOffHand.cardOne).first()
                        card2 = Card.query.filter_by(card_id = splitOffHand.cardTwo).first()
                        scards.append(card.image)
                        scards.append(card2.image)
                        card = Card.query.filter_by(card_id = splitOffHand.cardThree).first()
                        if card != None:
                            scards.append(card.image)
                        card = Card.query.filter_by(card_id = splitOffHand.cardFour).first()
                        if card != None:
                            scards.append(card.image)
                        card = Card.query.filter_by(card_id = splitOffHand.cardFive).first()
                        if card != None:
                            scards.append(card.image)
                        copySplit = scards.copy()
                        others.append(copySplit)
                        scards.clear()
                        
            e=False
            sessions = getSessionsPlaying()
            print(sessions)
            if (len(sessions) == 0):
                if (dl == False):
                    dealerLogic(1)
                dealers = []
                dealer = Hands.query.filter_by(dealerId = 1).first()
                card = Card.query.filter_by(card_id = dealer.cardOne).first()
                dealers.append(card.image)
                card = Card.query.filter_by(card_id = dealer.cardTwo).first()
                dealers.append(card.image)
                card = Card.query.filter_by(card_id = dealer.cardThree).first()
                if card != None:
                    dealers.append(card.image)
                #socketio.emit("reload")
                win = wincondtions(current_user.id, 1)
                print(yourHands)
                return render_template("finish.html", user = user, yourHands = yourHands, others = others, dealers = dealers, e=e, win=win)
            if(current_user.session == sessions[index] and len(sessions) != 0):
                e = True
                return render_template("game.html", user = user, yourHands = yourHands, others = others, dealers = dealers, betting = betting, e =e)
            return render_template("game.html", user = user, yourHands = yourHands, others = others, dealers = dealers, betting = betting, e=e)

    User.query.filter_by(id=user.id).update({'playing':1})
    db.session.commit()
    return render_template("game.html", user = user, betting = betting)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


def hit(uid):
    #print("in hit")
    user = User.query.filter_by(id = uid).first()
    c_id = getCard()
    #currentCard = deck.pop()
    #cardSplit = currentCard.split(" of ")
    #val = cardSplit[0]
    #symbol = cardSplit[1]
    card = Card.query.filter_by(card_id = c_id).first()
    card.dealt = 1
    #print(user.handid)
    hand = Hands.query.filter_by(hand_id= user.handid).first()
    if hand.cardThree == None:
        hand.cardThree = card.card_id
        hand.value += card.value
    elif hand.cardFour == None:
        hand.cardFour = card.card_id
        hand.value += card.value
    else:
        hand.cardFive = card.card_id
        hand.value += card.value
    db.session.commit()
    if (hand.value > 21):
        user.bust = 1
        db.session.commit()
    reload()

def split(userId):
    print("in split")
    global index
    #query hand and then query card from hand not like this!
    user = User.query.filter_by(id = userId).first()
    handOne = Hands.query.filter_by(hand_id= user.handid).first()
    cardOne = handOne.cardOne
    cardTwo = handOne.cardTwo
    originalHand = Hands.query.filter_by(hand_id= user.handid).first()
    c1 = Card.query.filter_by(card_id = cardOne).first()
    c2 = Card.query.filter_by(card_id = cardTwo).first()
    if c1.value == c2.value:
        print("split valid")
        hand = Hands()
        hand.cardOne = c2.card_id
        total = c2.value
        hand.userId = userId
        hand.value = total
        c_id = getCard()
        #currentCard = deck.pop()
        #cardSplit = currentCard.split(" of ")
        #val = cardSplit[0]
        #symbol = cardSplit[1]
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        hand.cardTwo = card.card_id
        hand.value += card.value
        db.session.add(hand)
        db.session.commit()
        User.query.filter_by(id=userId).update({'splitHand': hand.hand_id})
        db.session.commit()

        originalHand.value = c1.value
        c_id = getCard()
        #currentCard = deck.pop()
        #cardSplit = currentCard.split(" of ")
        #val = cardSplit[0]
        #symbol = cardSplit[1]
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        originalHand.cardTwo = card.card_id
        total = card.value
        originalHand.value += total
        db.session.commit()
        
        index += 1
        count = 0
        playing =  User.query.filter_by(playing=1)
        for player in playing:
            if player.bust != 1:
                count += 1
        if (index > count-1):
            index = 0
        reload()

def stand(userId):
    user = User.query.filter_by(id = userId).first()
    user.bust = 1
    db.session.commit()
    reload()

def dealerLogic(dealerId):
    global dl
    dl = True
    dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
    value = dealerHand.value
    if value < 17:
        c_id = getCard()
        #currentCard = deck.pop()
        #cardSplit = currentCard.split(" of ")
        #val = cardSplit[0]
        #symbol = cardSplit[1]
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        dealerHand.cardThree = card.card_id
        dealerHand.value += card.value
        db.session.commit()


def wincondtions(uid, dealerId):
    userHand = Hands.query.filter_by(userId=uid).first()
    dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
    user = User.query.filter_by(id=uid).first()
    userValue = userHand.value
    dealerValue = dealerHand.value
    userBet = user.bet  # need to change this

    if (userValue >= 22):  # bust
        user.cash = user.cash - userBet
    elif (dealerValue >= 22 and userValue < 22):  # no bust and dealer busts
        user.cash = user.cash + userBet
    elif (userValue >= dealerValue and userValue < 22):  # no bust and better than dealer
        user.cash = user.cash + userBet
    elif (userValue < dealerValue or userValue > 22):  # no bust and worse than dealer
        user.cash = user.cash - userBet
    elif (userValue == 21):
        userBet = userBet + userBet / 2
        user.cash = user.cash + (userBet)
    db.session.commit()

@socketio.on("betMoney")
def getBet(uid, bet):
    User.query.filter_by(id=uid).update({'bet': bet})
    print("got Bet")
    db.session.commit()

def reload():
    socketio.emit("reload")

@socketio.on("hit")
def handle_hit():
    global index
    hit(current_user.id)
    index += 1
    count = 0
    playing =  User.query.filter_by(playing=1)
    for player in playing:
        if player.bust != 1:
            count += 1
    if (index > count-1):
        index = 0

@socketio.on("stay")
def handle_stay():
    global index
    stand(current_user.id)
    index += 1
    count = 0
    playing =  User.query.filter_by(playing=1)
    for player in playing:
        if player.bust != 1:
            count += 1
    if (index > count-1):
        index = 0
    
@socketio.on("split")
def handle_split():
    split(current_user.id)

@socketio.on('con')
def handle_connection(data):
    print(data['data'])

@socketio.on("addPlayer")
def handle_player():
    global connected
    global user
    print("connected to game")
    User.query.filter_by(id=user.id).update({'session':request.sid})
    db.session.commit()


@socketio.on("test")
def handle_test():
    playing =  User.query.filter_by(playing=1)
    sessionIds=[]
    for player in playing:
        sessionIds.append(player.session)
    print("activate")
    socketio.emit("activate", to=sessionIds[index])

@socketio.on("checkTableSize")
def checkTable():
    global connected
    global e

@socketio.on("dealOne")
def reloadOnce():
    global reloadFirstDeal
    reloadFirstDeal = True


@socketio.on("gameRepeat")
def gameRepeat():
    print("repeat")
    databaseReset()
    return redirect('/game')

@socketio.on("gameReset")
def gameReset():
    print("reset")
    databaseReset()

def databaseReset():
    numberPlaying = User.query.all()
    # numberPlaying = User.query.filter_by(playing=1).count() + 1
    User.query.filter_by(playing=1).update({'personBet': 0})
    User.query.filter_by(playing=1).update({'bust': 0})
    User.query.filter_by(playing=1).update({'splitHand': None})
    User.query.filter_by(playing=1).update({'playing': 0})
    db.session.commit()
    Card.query.filter_by(dealt=1).update({'dealt': 0})
    db.session.commit()
    db.session.execute('DELETE FROM Hands')
    db.session.commit()

#disconnect set playing to 0 remove their hand set bet to 0 session to 0
@socketio.on('disconnect')
def handle_disconnect():
    print("disconnect")



if __name__ == '__main__':
    serve(app, port=5000, threads=25)
