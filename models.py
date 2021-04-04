from werkzeug.security import check_password_hash
import datetime
from pymongo import MongoClient

mongoClient = MongoClient('mongodb://localhost:27017/')
db = mongoClient['pytrade']

# users
def post_sign_up(request_data):
    collection = db['users']
    user_data = collection.find_one(filter={'email': request_data['email']})
    error = None
    if user_data:
        error = '이미 존재하는 사용자입니다.'
    else:
        user_data = collection.find_one(sort=[('create_time', -1)])
        if user_data:
            user_id = user_data['user_id'] + 1
        else:
            user_id = 1
        request_data['create_time'] = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        request_data['user_id'] = user_id
        collection.insert(request_data)
    return error

def post_login(request_data):
    collection = db['users']
    error = None
    user_data = collection.find_one(filter={'email': request_data['email']})
    if not user_data:
        error = "존재하지 않는 사용자입니다."
    elif not check_password_hash(user_data['password'], request_data['password']):
        error = "비밀번호가 올바르지 않습니다."
    return error, user_data

# account
def get_account_list():
    collection = db['account']
    data = collection.find_one({'account_list':{'$exists': 'true'}})
    if data:
        return data['account_list']
    else:
        return data

def update_account_list(account_list):
    collection = db['account']
    update = {'account_list':account_list}
    collection.update_one({'account_list': {'$exists':'true'}}, {'$set':update}, upsert=True)

def get_account_info(account):
    collection = db['account']
    date = datetime.datetime.today().strftime("%Y%m%d")
    account_info = collection.find_one({'date':date, 'account':account})
    return account_info

def update_account_info(update):
    collection = db['account']
    date = datetime.datetime.today().strftime("%Y%m%d")
    update['date'] = date
    collection.update_one({'date':date, 'account':update['account']}, {'$set':update}, upsert=True)

def update_profit(account, profit):
    collection = db['profit']
    date = datetime.datetime.today().strftime("%Y%m%d")
    update = profit
    update['date'] = date
    update['account'] = account
    collection.update_one({'date':date, 'account':account}, {'$set':update}, upsert=True)

def update_myStock(account, code, myStock):
    collection = db['stock']
    date = datetime.datetime.today().strftime("%Y%m%d")
    update = myStock
    update['date'] = date
    update['account'] = account
    update['code'] = code
    collection.update_one({'date':date, 'account':account, 'code':code}, {'$set':update}, upsert=True)

def get_chart(code):
    collection = db['chart']
    isNext = True
    today = datetime.date.today()
    # except weekend
    if today.weekday() == 5:
        today = today - datetime.timedelta(days=1)
    elif today.weekday() == 6:
        today = today - datetime.timedelta(days=2)
    date = today.strftime("%Y%m%d")
    lastDate = None
    chart = []
    lastChart = collection.find_one({'code':code}, sort=[('date', -1)])
    if lastChart is not None:
        lastDate = lastChart['date']
        chartData = collection.find({'code':code}, sort=[('date', -1)])
        for data in chartData:
            del data['_id']
            chart.append(data)
    if date == lastDate:
        isNext = False
    return isNext, lastDate, chart

def update_chart(code, chart):
    collection = db['chart']
    date = datetime.datetime.today().strftime("%Y%m%d")
    for data in chart:
        update = data
        update['code'] = code
        collection.update_one({'code':code, 'date':data['date']}, {'$set':update}, upsert=True)





