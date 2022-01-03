import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred,{'databaseURL':'https://parkinglot-107e6-default-rtdb.firebaseio.com/'})

def get_Account(carId):
    ref = db.reference('Plates')
    data = ref.get()
    if carId in data:
        return data[carId]
    else:
        return ""

def get_LineToken(account):
    ref = db.reference('Users')
    return ref.get()[account]['LineToken']

def registerMember(account,password,phone,carid,lineToken):
    ref = db.reference()
    if ref.child("Users/" + account).get() == None and ref.child('Plates/' + carid).get() == None:
        data = {
            "Password" : password,
            "Phone" : phone,
            "CarId" : carid,
            "LineToken" : lineToken
        }
        ref.child("Users/" + account).update(data)
        ref.child("Plates").update({carid : account})
        return "註冊成功"
    else:
        return "用戶已存在"
    
def updateMemberPlate(account,password,carid):
    ref = db.reference()
    userData = ref.child('Users/'+account).get()
    if userData != None:
        if userData['Password'] == password:
            oldPlates = userData['CarId']
            ref.child('Users/'+account+"/CarId").set(carid)
            ref.child('Plates/'+oldPlates).delete()
            ref.child('Plates/'+carid).set(account)
            return "修改成功"
        else:
            return "帳號或密碼錯誤"
    else:
        return "帳號或密碼錯誤"