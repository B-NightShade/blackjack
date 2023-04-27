# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from waitress import serve
from flask_socketio import SocketIO, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, \
    logout_user, current_user, login_required
import threading


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
    done = db.Column(db.Integer)

user = User()
lock = threading.Lock()

@login_manager.user_loader
def load_user(uid): 
    global user
    user = User.query.get(uid)
    return user
    


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
    global amountPlaying

    amountPlaying = amountPlaying + 1
    print("dealing")
    
    for player in players:
        c_id = getCard()
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        hand = Hands()
        hand.cardOne = card.card_id
        hand.done = 0
        total = card.value

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
    card = Card.query.filter_by(card_id = c_id).first()
    card.dealt = 1
    hand.cardOne = card.card_id
    hand.done = 0
    dealerTotal = card.value
    
    c_id = getCard()
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
    #change this to playing hands
    viableHands = Hands.query.filter_by(done = 0)
    hands = []
    for hand in viableHands:
        if (hand.dealerId != 1):
            hands.append(hand.hand_id)
    print(hands)
    return hands

connected = 0
reloadFirstDeal = False
dealt = False
index = 0
dl = False
amountInGame = 0
amountPlaying = 1
addMore = True

@app.route('/', methods=['GET','POST'])
def home():
    global user
    a= False
    #b = True ##needs login form
    c = False
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
                    #b = False #no longer needs login form
                    c = False
                    if addMore == False:
                        c = True
                        a = False
                    tableSize = User.query.filter_by(playing=1).count()
                    if (tableSize >= 3):
                        c = True
                        a = False
                    return render_template('home.html', a=a,c=c)
                else:
                    return render_template('login.html')
            else:
                return render_template('login.html')
        else:
            return redirect('/game')
    return render_template('login.html')

@app.route('/game', methods=['GET','POST'])
@login_required
def game():
    #set playing to true
    global user
    global reloadFirstDeal
    global dealt
    global index
    global dl
    global buttonPressed
    global amountPlaying
    global amountInGame
    global addMore

    betting = True
    if request.method == "POST":
        lock.acquire();
        userid = current_user.id
        user = User.query.filter_by(id=userid).first()
        User.query.filter_by(id=userid).update({'personBet':1})
        userBet = request.form['bet']
        User.query.filter_by(id=userid).update({'bet':userBet})

        db.session.commit()
        lock.release()
        numberPlaying = User.query.filter_by(playing=1).count()
        numberBet = User.query.filter_by(personBet=1).count()
        amountInGame = numberBet
        print("amount in game = "+ str(amountInGame))
        print("amount playing = "+ str(amountPlaying))
        if (numberPlaying == numberBet):
            if amountInGame == amountPlaying:
                addMore = False
                print("addmore is false")
            if (reloadFirstDeal == False and dealt == False):
                print("ready to deal")
                playing =  User.query.filter_by(playing=1)
                deal(playing)
                socketio.emit("reload")
        

            betting = False
            yourHands = []
            yourHand = []
            sHand = []
            lock.acquire()
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
                    
                    if(player.splitHand != None):
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
            lock.release()          
            e=False
            sessions = getSessionsPlaying()
            print(sessions)
            if (len(sessions) == 0):
                if (dl == False):
                    dealerLogic(1)
                dealers = []
                lock.acquire()
                dealer = Hands.query.filter_by(dealerId = 1).first()
                card = Card.query.filter_by(card_id = dealer.cardOne).first()
                dealers.append(card.image)
                card = Card.query.filter_by(card_id = dealer.cardTwo).first()
                dealers.append(card.image)
                card = Card.query.filter_by(card_id = dealer.cardThree).first()
                if card != None:
                    dealers.append(card.image)
                card = Card.query.filter_by(card_id = dealer.cardFour).first()
                if card != None:
                    dealers.append(card.image)
                card = Card.query.filter_by(card_id = dealer.cardFive).first()
                if card != None:
                    dealers.append(card.image)
                #socketio.emit("reload")
                buttonPressed = False
                win = wincondtions(current_user.id, 1)
                print(yourHands)
                splitEnd = splitWinConditions(current_user.id,1)
                lock.release()
                return render_template("finish.html", user = user, yourHands = yourHands, others = others, dealers = dealers, e=e, win=win, splitEnd=splitEnd)
            #if user.hand or user.split =sessions[index]
            if(current_user.handid == sessions[index] and len(sessions) != 0):
                e = True
                return render_template("game.html", user = user, yourHands = yourHands, others = others, dealers = dealers, betting = betting, e =e)
            if(current_user.splitHand == sessions[index] and len(sessions) != 0):
                split = True
                return render_template("game.html", user = user, yourHands = yourHands, others = others, dealers = dealers, betting = betting, split=split)
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
    user = User.query.filter_by(id = uid).first()
    c_id = getCard()
    card = Card.query.filter_by(card_id = c_id).first()
    card.dealt = 1
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
        c1 = Card.query.filter_by(card_id = hand.cardOne).first()
        c2 = Card.query.filter_by(card_id = hand.cardTwo).first()
        c3 = Card.query.filter_by(card_id = hand.cardThree).first()
        c4 = Card.query.filter_by(card_id = hand.cardFour).first()
        c5 = Card.query.filter_by(card_id = hand.cardFive).first()
        if(c1.symbol=='ace' and c1.dealt !=2):
            hand.value = hand.value - 10
            c1.dealt =2
            db.session.commit()
        if(c2.symbol=='ace' and c2.dealt != 2 and hand.value >21):
            hand.value = hand.value - 10
            c2.dealt =2
            db.session.commit()
        if(c3 != None):
            if(c3.symbol=='ace' and c3.dealt != 2 and hand.value >21):
                hand.value = hand.value - 10
                c3.dealt =2
                db.session.commit()
        if(c4 != None):
            if(c4.symbol=='ace' and c4.dealt != 2 and hand.value >21):
                hand.value = hand.value - 10
                c4.dealt =2
                db.session.commit()
        if(c5 != None):
            if(c5.symbol=='ace' and c5.dealt != 2 and hand.value >21):
                hand.value = hand.value - 10
                c5.dealt =2
                db.session.commit()
        else:
            #user.bust = 1
            hand.done = 1
            db.session.commit()
    reload()
    
def hitsplit(uid):
    user = User.query.filter_by(id = uid).first()
    c_id = getCard()
    card = Card.query.filter_by(card_id = c_id).first()
    card.dealt = 1
    hand = Hands.query.filter_by(hand_id= user.splitHand).first()
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
        c1 = Card.query.filter_by(card_id = hand.cardOne).first()
        c2 = Card.query.filter_by(card_id = hand.cardTwo).first()
        c3 = Card.query.filter_by(card_id = hand.cardThree).first()
        c4 = Card.query.filter_by(card_id = hand.cardFour).first()
        c5 = Card.query.filter_by(card_id = hand.cardFive).first()
        if(c1.symbol=='ace' and c1.dealt !=2):
            hand.value = hand.value - 10
            c1.dealt =2
            db.session.commit()
        elif(c2.symbol=='ace' and c2.dealt != 2 and hand.value >21):
            hand.value = hand.value - 10
            c2.dealt =2
            db.session.commit()
        if(c3 != None):
            if(c3.symbol=='ace' and c3.dealt != 2 and hand.value >21):
                hand.value = hand.value - 10
                c3.dealt =2
                db.session.commit()
        if(c4 != None):
            if(c4.symbol=='ace' and c4.dealt != 2 and hand.value >21):
                hand.value = hand.value - 10
                c4.dealt =2
                db.session.commit()
        if(c5 != None):
            if(c5.symbol=='ace' and c5.dealt != 2 and hand.value >21):
                hand.value = hand.value - 10
                c5.dealt =2
                db.session.commit()
        else:
            #user.bust = 1
            hand.done = 1
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
    if (c1.value == c2.value) and (user.splitHand == None) and ((user.bet * 2)<=user.cash):
        print("split valid")
        hand = Hands()
        hand.done = 0
        hand.cardOne = c2.card_id
        total = c2.value
        hand.userId = userId
        hand.value = total
        c_id = getCard()
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
        card = Card.query.filter_by(card_id = c_id).first()
        card.dealt = 1
        originalHand.cardTwo = card.card_id
        total = card.value
        originalHand.value += total
        db.session.commit()
        
        index += 1
        count = 0
        viableHands = Hands.query.filter_by(done = 0)
        for hand in viableHands:
            if (hand.dealerId != 1):
                if(hand.done != 1):
                    count += 1
        if (index > count-1):
            index = 0
        reload()

def stand(userId):
    user = User.query.filter_by(id = userId).first()
    hand = Hands.query.filter_by(hand_id = user.handid).first()
    hand.done = 1
    db.session.commit()
    reload()

def standsplit(userId):
    user = User.query.filter_by(id = userId).first()
    hand = Hands.query.filter_by(hand_id = user.splitHand).first()
    hand.done = 1
    db.session.commit()
    reload()


def dealerLogic(dealerId):
    global dl
    dl = True
    dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
    value = dealerHand.value
    if value < 17:
        c_id = getCard()
        card = Card.query.filter_by(card_id=c_id).first()
        card.dealt = 1
        dealerHand.cardThree = card.card_id
        dealerHand.value += card.value
        db.session.commit()
        if dealerHand.cardThree == 'ace' and value < 21:
            dealerHand.value = dealerHand.value - 10
            card.dealt = 2
            db.session.commit()
    dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
    value = dealerHand.value
    if value < 17:
        c_id = getCard()
        card = Card.query.filter_by(card_id=c_id).first()
        card.dealt = 1
        dealerHand.cardFour = card.card_id
        dealerHand.value += card.value
        db.session.commit()
        if dealerHand.cardThree == 'ace' and value < 21:
            dealerHand.value = dealerHand.value - 10
            card.dealt = 2
            db.session.commit()
        if dealerHand.cardFour == 'ace' and value < 21:
            dealerHand.value = dealerHand.value - 10
            card.dealt = 2
            db.session.commit()
    dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
    value = dealerHand.value
    if value < 17:
        c_id = getCard()
        card = Card.query.filter_by(card_id=c_id).first()
        card.dealt = 1
        dealerHand.cardFive = card.card_id
        dealerHand.value += card.value
        db.session.commit()
        if dealerHand.cardThree == 'ace' and value < 21:
            dealerHand.value = dealerHand.value - 10
            card.dealt = 2
            db.session.commit()
        if dealerHand.cardFour == 'ace' and value < 21:
            dealerHand.value = dealerHand.value - 10
            card.dealt = 2
            db.session.commit()
        if dealerHand.cardFive == 'ace' and value < 21:
            dealerHand.value = dealerHand.value - 10
            card.dealt = 2
            db.session.commit()

def wincondtions(uid, dealerId):
    userHand = Hands.query.filter_by(userId=uid).first()
    dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
    user = User.query.filter_by(id=uid).first()
    userValue = userHand.value
    dealerValue = dealerHand.value
    userBet = user.bet  # need to change this

    if (userValue == dealerValue and userValue <=21): #no bust and tie
        return "push"
    elif (userValue >= 22):  # bust
        user.cash = user.cash - userBet
        db.session.commit()
        return "lost"
    elif (dealerValue >= 22 and userValue < 22):  # no bust and dealer busts
        user.cash = user.cash + userBet
        db.session.commit()
        return "win"
    elif (userValue >= dealerValue and userValue < 22):  # no bust and better than dealer
        user.cash = user.cash + userBet
        db.session.commit()
        return "win"
    elif (userValue < dealerValue or userValue > 22):  # no bust and worse than dealer
        user.cash = user.cash - userBet
        db.session.commit()
        return "lost"
    elif (userValue == 21):
        userBet = userBet + userBet / 2
        user.cash = user.cash + (userBet)
        db.session.commit()
        return "win"
    db.session.commit()

def splitWinConditions(uid, dealerId):
    user = User.query.filter_by(id = uid).first()
    if (user.splitHand != None):
        userHand = Hands.query.filter_by(hand_id= user.splitHand).first()
        dealerHand = Hands.query.filter_by(dealerId=dealerId).first()
        user = User.query.filter_by(id=uid).first()
        userValue = userHand.value
        dealerValue = dealerHand.value
        userBet = user.bet  # need to change this
    
        if (userValue == dealerValue and userValue <=21): #no bust and tie
            return "push"
        elif (userValue >= 22):  # bust
            user.cash = user.cash - userBet
            db.session.commit()
            return "lost"
        elif (dealerValue >= 22 and userValue < 22):  # no bust and dealer busts
            user.cash = user.cash + userBet
            db.session.commit()
            return "win"
        elif (userValue >= dealerValue and userValue < 22):  # no bust and better than dealer
            user.cash = user.cash + userBet
            db.session.commit()
            return "win"
        elif (userValue < dealerValue or userValue > 22):  # no bust and worse than dealer
            user.cash = user.cash - userBet
            db.session.commit()
            return "lost"
        elif (userValue == 21):
            userBet = userBet + userBet / 2
            user.cash = user.cash + (userBet)
            db.session.commit()
            return "win"
        db.session.commit()
    return "none"

@socketio.on("beginningOfGame")
def beginningOfGame():
    print("game start")
    databaseReset()


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
    viableHands = Hands.query.filter_by(done = 0)
    for hand in viableHands:
        if (hand.dealerId != 1):
            if(hand.done != 1):
                count += 1
    if (index > count-1):
        index = 0


@socketio.on("stay")
def handle_stay():
    global index
    stand(current_user.id)
    index += 1
    count = 0
    viableHands = Hands.query.filter_by(done = 0)
    for hand in viableHands:
        if (hand.dealerId != 1):
            if(hand.done != 1):
                count += 1
    if (index > count-1):
        index = 0

    
@socketio.on("hitsplit")
def handle_hitsplit():
    global index
    hitsplit(current_user.id)
    index += 1
    count = 0
    viableHands = Hands.query.filter_by(done = 0)
    for hand in viableHands:
        if (hand.dealerId != 1):
            if(hand.done != 1):
                count += 1
    if (index > count-1):
        index = 0

@socketio.on("staysplit")
def handle_staysplit():
    global index
    standsplit(current_user.id)
    index += 1
    count = 0
    viableHands = Hands.query.filter_by(done = 0)
    for hand in viableHands:
        if (hand.dealerId != 1):
            if(hand.done != 1):
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
    global buttonPressed
    buttonPressed = True
    print("repeat")
    databaseReset()
    socketio.emit("gameToRepeat")
    #return redirect(url_for('game'))

@socketio.on("gameReset")
def gameReset():
    print("reset")
    databaseReset()
    socketio.emit("gameToLogout")

@socketio.on("gameLogOut")
def gameLogOut(): #if this breaks name used to be gameReset
    global buttonPressed
    if buttonPressed == False:
        print("logout")
        databaseReset()
        #socketio.emit('logout')
        socketio.emit("gameToLogout")
 

def databaseReset():
    global reloadFirstDeal
    global dealt
    global index
    global dl
    global addMore
    global amountInGame
    global amountPlaying
    reloadFirstDeal = False
    dealt = False
    index = 0
    dl = False
    addMore = True
    amountInGame = 0
    amountPlaying = 1
    numberPlaying = User.query.all()
    # numberPlaying = User.query.filter_by(playing=1).count() + 1
    User.query.filter_by(playing=1).update({'personBet': 0})
    User.query.filter_by(playing=1).update({'bust': 0})
    User.query.filter_by(playing=1).update({'splitHand': None})
    User.query.filter_by(playing=1).update({'playing': 0})
    db.session.commit()
    Card.query.filter_by(dealt=1).update({'dealt': 0})
    Card.query.filter_by(dealt=2).update({'dealt': 0})
    db.session.commit()
    db.session.execute('DELETE FROM Hands')
    db.session.commit()

#disconnect set playing to 0 remove their hand set bet to 0 session to 0
@socketio.on('disconnect')
def handle_disconnect():
    print("disconnect")


if __name__ == '__main__':
    serve(app, port=5000, threads=25)
