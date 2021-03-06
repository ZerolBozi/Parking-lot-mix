import myDatabase
import findPlate
import threading
import requests
import pyttsx3
import time
import math
import json
import cv2
import os
from flask import Flask, request, render_template, session, flash, url_for, redirect
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/auth")
def auth():
    url = 'https://notify-bot.line.me/oauth/authorize?response_type=code&scope=notify&response_mode=form_post&state=f094a459&client_id=5Fwa1d2JrCeaTnwGuqQB0x&redirect_uri=http://127.0.0.1:5000/callback'
    return redirect(url)

@app.route("/callback",methods=['POST'])
def callback():
    if request.method == 'POST':
        client_id = "5Fwa1d2JrCeaTnwGuqQB0x"
        redirect_uri = "http://127.0.0.1:5000/callback"
        client_secret = "pG5PipiHg1aySwy6VFdwk0hEPq2GBQUm24LQzoejfbh"
        code = request.form.get('code')
        token_URL = "https://notify-bot.line.me/oauth/token?grant_type=authorization_code&redirect_uri={}&client_id={}&client_secret={}&code={}".format(redirect_uri, client_id, client_secret, code)
        token_r = requests.post(token_URL)
        if token_r.status_code == requests.codes.ok:
            access_token = json.loads(token_r.text)
            lineToken = access_token['access_token']
            session['access_token'] = lineToken
            session.permanent = True
            flash("連動成功!","success")
        else:
            flash("連動失敗!","success")
        return redirect("/register")

@app.route("/register",methods=['GET','POST'])
def register():
    if request.method == 'POST':
        account = request.form.get('account')
        password = request.form.get('password')
        phone = request.form.get('phone')
        carid = request.form.get('carid')
        token = request.form.get('token')
        ret = myDatabase.registerMember(account,password,phone,carid,token)
        session.pop('access_token',None)
        return ret
    elif request.method == 'GET':
        return render_template('register.html')

@app.route('/setting',methods=['GET'])
def plateSetting():
    if request.method == 'GET':
        return render_template('setting.html')

@app.route('/updatePlate',methods=['POST'])
def updatePlate():
    if request.method == 'POST':
        account = request.form.get('account')
        password = request.form.get('password')
        carid = request.form.get('carid')
        ret = myDatabase.updateMemberPlate(account,password,carid)
        return ret

class Client:
    def __init__(self,account,member,lineToken,flag,startTime):
        self.a = account
        self.m = member
        self.l = lineToken
        self.f = flag
        self.st = startTime

    def getSpendt(self):
        spendt = math.ceil(round(get_Time(2) - self.st,0)/3600)
        return spendt
    
    def getSpend(self):
        base = 20
        spend = self.getSpendt()*base
        return spend

def send_LineNotify(lineToken,msg):
    url = "https://notify-api.line.me/api/notify"
    headers = {
        'Content-Type' : 'application/x-www-form-urlencoded',
        'Authorization' : 'Bearer ' + lineToken
    }
    payload = {'message' : msg}
    r = requests.post(url,headers=headers,params=payload)
    return r.status_code

#0 日期+時間 , 1 語音播放格式 , 2 時間計算專用 , 3 dbg
def get_Time(p):
    if p==0:
        return time.strftime("%Y/%m/%d\n%H:%M:%S",time.localtime())
    elif p==1:
        return time.strftime("%m月%d日 %I:%M:%S",time.localtime())
    elif p==2:
        return time.time()
    elif p==3:
        return time.strftime("%H:%M:%S", time.localtime())
    
def notify_Thread(account,lineToken):
    print(f"[Debug {get_Time(3)}] User：{account} Notify thread working.")
    index = dic[account]
    send = 0
    while clients[index].f == 1:
        nextt = clients[index].getSpendt()*3600
        if nextt != 0:
            if send == 0 and nextt - round(get_Time(2) - clients[index].st,0) <= 300:
                print(f"[Debug {get_Time(3)}] User：{account} Next spend amount.")
                send_LineNotify(lineToken,"5分鐘後即將到達下一個收費金額!!")
                send = 1
            elif send == 1 and nextt - round(get_Time(2) - clients[index].st,0) > 300:
                send = 0
        time.sleep(1)
    del clients[index]
    print(f"[Debug {get_Time(3)}] User：{account} Notify thread stopping.")
    return

def say(msg):
    engine = pyttsx3.init()
    engine.say(msg)
    engine.runAndWait()

def process(plate):
    print(f"[Debug {get_Time(3)}] From database get account...")
    account = myDatabase.get_Account(plate)
    if account == "":
        account = plate
        lineToken = 0
        mem = 0
    else:
        print(f"[Debug {get_Time(3)}] From database get lineToken...")
        lineToken = myDatabase.get_LineToken(account)
        print(f"[Debug {get_Time(3)}] LineToken：{lineToken}")
        mem = 1
    print(f"[Debug {get_Time(3)}] Account：{account}")
    #入場
    if account not in dic:
        print(f"[Debug {get_Time(3)}] User：{account} Enter the parking lot")
        clients.append(Client(account,mem,lineToken,flag=1,startTime=get_Time(2)))
        dic[account] = len(clients)-1
        if mem == 1:
            send_LineNotify(lineToken,f'\n歡迎光臨 {account}\n您入場的時間是\n{get_Time(0)}\n車牌號碼為 {plate}')
            print(f"[Debug {get_Time(3)}] User：{account} Start notify thread...")
            t = threading.Thread(target=notify_Thread,args=(account,lineToken,))
            t.start()
            thread_list.append(t)
        say(f"歡迎光臨，您入場的時間是{get_Time(1)}車牌號碼為{plate}")
    #出場
    else:
        print(f"[Debug {get_Time(3)}] User：{account} Leave the parking lot")
        index = dic[account]
        spendt = clients[index].getSpendt()
        print(f"[Debug {get_Time(3)}] User：{account} Spend time：{spendt}")
        del dic[account]
        spend = clients[index].getSpend()
        print(f"[Debug {get_Time(3)}] User：{account} Spend money：{spend}")
        if clients[index].m == 1:
            discount = myDatabase.getDiscount(account)
            discounts = myDatabase.addDiscount(account,spend)
            send_LineNotify(lineToken,f'\n謝謝光臨 {account}\n您出場的時間是\n{get_Time(0)}\n車牌號碼為 {plate}')
            clients[index].f = 0
            if discount != 0:
                send_LineNotify(lineToken,f'\n------消費明細------\n會員帳號：{account}\n車牌號碼：{plate}\n停車時數：{spendt}小時\n消費金額： {spend-discount}元\n現有折價券張數：{discounts}')
                say(f"總共停了{spendt}小時，金額為{spend}元，扣除折價券後的金額為{spend-discount}元")
            else:
                send_LineNotify(lineToken,f'\n------消費明細------\n會員帳號：{account}\n車牌號碼：{plate}\n停車時數：{spendt}小時\n消費金額： {spend}元')
                say(f"總共停了{spendt}小時，金額為{spend}元")
        else:
            del clients[index]
            say(f"總共停了{spendt}小時，金額為{spend}元，請刷卡")
    return main()

def main():
    test = 1
    if test:
        plate = findPlate.detect(1,'1.jpg')
        print(f'[Debug {get_Time(3)}] Plate："{plate}"')
        thread = threading.Thread(target=process,args=(plate,))
        thread.start()
    else:
        cap = cv2.VideoCapture(0,cv2.CAP_DSHOW) # 0 = 筆電鏡頭 1 = 外接鏡頭
        plateList = []
        # 搜集30組數據 利用眾數獲得車牌號碼
        while len(plateList)<30:
            ret,frame = cap.read()
            cv2.imshow("Camera",frame)
            plate = findPlate.detect(0,frame)
            print(f'[Debug {get_Time(3)}] Plate："{plate}"')
            if plate != "No Plate":
                plateList.append(plate)
            # time.sleep(0.1)
            if cv2.waitKey(5)==27:
                quit()
                break
        cap.release()
        cv2.destroyAllWindows()
        plate = max(plateList,key=plateList.count)
        threading.Thread(target = process,args=(plate,)).start()

if __name__ == "__main__": 
    global thread_list
    global clients
    global dic
    thread_list = []
    clients = []
    dic = dict()
    threading.Thread(target=app.run).start()
    os.system('cls')
    print(f"[Debug {get_Time(3)}] Initialization...")
    time.sleep(1)
    threading.Thread(target=main).start()
