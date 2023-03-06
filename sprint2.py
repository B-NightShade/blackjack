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
    playing = db.Column(db.Integer)
    bet = db.Column(db.Integer)
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

symbol = [2, 3, 4, 5, 6, 7, 8, 9, 10, "jack", "queen", "king", "ace"]


suit = ["spades", "diamonds", "hearts", "clubs"]

deck = []
for i in range(0,3):
    for v in symbol:
        for s in suit:
            deck.append(str(v) + " of " + s)
random.shuffle(deck)

def getVal(symbol):
    if symbol == "jack" or symbol == "queen" or symbol == "king":
        value = 10
    elif  symbol == "ace":
        value = 11
    else:
        value=int(symbol)
    return int(value)

def deal(players):
    global dealt
    print("dealing")
    for player in players:
        currentCard = deck.pop()
        cardSplit = currentCard.split(" of ")
        val = cardSplit[0]
        symbol = cardSplit[1]
        card = Card.query.filter_by(symbol=val, suit=symbol).first()
        card.dealt = 1
        hand = Hands()
        hand.cardOne = card.card_id
        
        currentCard2 = deck.pop()
        cardSplit = currentCard2.split(" of ")
        val = cardSplit[0]
        symbol = cardSplit[1]
        card = Card.query.filter_by(symbol=val, suit=symbol).first()
        card.dealt = 1
        hand.cardTwo = card.card_id
    
        hand.userId = player.id;
        db.session.add(hand)
        db.session.commit()
    hand = Hands()
    currentCard = deck.pop()
    cardSplit = currentCard.split(" of ")
    val = cardSplit[0]
    symbol = cardSplit[1]
    card = Card.query.filter_by(symbol=val, suit=symbol).first()
    card.dealt = 1
    hand.cardOne = card.card_id
    
    currentCard2 = deck.pop()
    cardSplit = currentCard2.split(" of ")
    val = cardSplit[0]
    symbol = cardSplit[1]
    card = Card.query.filter_by(symbol=val, suit=symbol).first()
    card.dealt = 1
    hand.cardTwo = card.card_id
    hand.dealerId = 1;
    db.session.add(hand)
    db.session.commit()
    dealt = True


connected = 0
reloadFirstDeal = False
dealt = False
index = 0

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
    betting = True
    if request.method == "POST":
        userid = current_user.id
        user = User.query.filter_by(id=userid).first()
        User.query.filter_by(id=userid).update({'bet':1})
        db.session.commit()
        numberPlaying = User.query.filter_by(playing=1).count()
        numberBet = User.query.filter_by(bet=1).count()
        if (numberPlaying == numberBet):
            if (reloadFirstDeal == False and dealt == False):
                print("ready to deal")
                playing =  User.query.filter_by(playing=1)
                deal(playing)
                socketio.emit("reload")
            
            
            betting = False
            yourHand = []
            Hand = Hands.query.filter_by(userId= user.id).first()
            card = Card.query.filter_by(card_id = Hand.cardOne).first()
            yourHand.append(card.image)
            card = Card.query.filter_by(card_id = Hand.cardTwo).first()
            yourHand.append(card.image)
            #print(yourHand)
            
            dealers = []
            dealer = Hands.query.filter_by(dealerId = 1).first()
            card = Card.query.filter_by(card_id = dealer.cardOne).first()
            #print(card.image)
            dealers.append(card.image)
            card = Card.query.filter_by(card_id = dealer.cardTwo).first()
            dealers.append(card.back)
            #print(dealers)
            
            others = []
            cards = []
            playing =  User.query.filter_by(playing=1)
            for player in playing:
                if(player.id != user.id):
                    hand =  Hands.query.filter_by(userId= player.id).first()
                    card = Card.query.filter_by(card_id = hand.cardOne).first()
                    card2 = Card.query.filter_by(card_id = hand.cardTwo).first()
                    cards.append(card.image)
                    cards.append(card2.image)
                    cardsCopy = cards.copy()
                    others.append(cardsCopy)
                    cards.clear()
            return render_template("game.html", user = user, yourHand = yourHand, others = others, dealers = dealers, betting = betting)
    User.query.filter_by(id=user.id).update({'playing':1})
    db.session.commit()
    return render_template("game.html", user = user, betting = betting)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))



@socketio.on('con')
def handle_connection(data):
    print(data['data'])

@socketio.on("addPlayer")
def handle_player():
    global connected
    global user
    print("connected to game")
    print(request.sid)
    User.query.filter_by(id=user.id).update({'session':request.sid})
    room = request.sid
    join_room(room)
    db.session.commit()
    connected += 1

#disconnect set playing to 0 remove their hand set bet to 0 session to 0

@socketio.on("test")
def handle_test():
    playing =  User.query.filter_by(playing=1)
    sessionIds=[]
    for player in playing:
        sessionIds.append(player.session)
    socketio.emit("activate", to=sessionIds[index])
    ##print(sessionIds[index])
    ##print("on submit??")

@socketio.on("checkTableSize")
def checkTable():
    global connected
    global e

@socketio.on("dealOne")
def reloadOnce():
    global reloadFirstDeal 
    reloadFirstDeal = True

    
@socketio.on('disconnect')
def handle_disconnect():
    global index
    room = request.sid
    leave_room(room)
    ##print(sessionIds)


if __name__ == '__main__':
    #app.run()
    serve(app, port=5000, threads=15)
   
