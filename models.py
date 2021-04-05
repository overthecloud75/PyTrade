import copy
from werkzeug.security import check_password_hash
import datetime
from views.config import page_default
from utils import paginate
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
    data = collection.find_one({'account_list':{'$exists':'true'}})
    if data:
        return data['account_list']
    else:
        return data

def update_account_list(account_list):
    collection = db['account']
    update = {'account_list':account_list}
    collection.update_one({'account_list': {'$exists':'true'}}, {'$set':update}, upsert=True)

def get_account_info(account, page=1, is_paging=False):
    collection = db['account']
    date = datetime.datetime.today().strftime("%Y%m%d")
    if is_paging:
        per_page = page_default['per_page']
        offset = (page - 1) * per_page
        data_list = collection.find({'date':date, 'account':account}).limit(per_page).skip(offset)
        count = data_list.count()
        paging = paginate(page, per_page, count)
        return paging, data_list
    else:
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
    update['user'] = account
    collection.update_one({'date':date, 'account':account}, {'$set':update}, upsert=True)

# code
def get_code(codeName):
    collection = db['code']
    data = collection.find_one({'codeName':codeName})
    if data is None:
        return data
    else:
        return data['code']

def update_code(update):
    collection = db['code']
    if 'codeName' in update and 'code' in update:
        collection.update_one({'codeName':update['codeName']}, {'$set':update}, upsert=True)
    else:
        pass

# mystock
def get_myStock(account, code=None, page=1, is_paging=False):
    collection = db['stock']
    if is_paging:
        per_page = page_default['per_page']
        offset = (page - 1) * per_page
        data_list = collection.find({'account':account}, sort=[('date', -1)]).limit(per_page).skip(offset)
        count = data_list.count()
        paging = paginate(page, per_page, count)
        return paging, data_list
    else:
        data_list = collection.find({'account': account})
        return data_list

def update_myStock(account, code, myStock):
    collection = db['stock']
    date = datetime.datetime.today().strftime("%Y%m%d")
    update = myStock
    update['date'] = date
    update['user'] = account
    update['code'] = code
    collection.update_one({'date':date, 'account':account, 'code':code}, {'$set':update}, upsert=True)

def get_chart(code, isJson=False):
    collection = db['chart']
    isNext = True
    today = datetime.date.today()
    # except weekend
    if today.weekday() == 5:
        today = today - datetime.timedelta(days=1)
    elif today.weekday() == 6:
        today = today - datetime.timedelta(days=2)
    date = today.strftime("%Y%m%d")
    chart = []
    if isJson:
        chartData = collection.find({'code':code}, sort=[('date', -1)]).limit(360)
        for data in chartData:
            del data['_id']
            chart.append(data)
        chart.reverse()
        return chart
    else:
        lastDate = None
        lastChart = collection.find_one({'code':code}, sort=[('date', -1)])
        if lastChart is not None:
            lastDate = lastChart['date']
            chartData = collection.find({'code':code}, sort=[('date', -1)]).limit(360)
            for data in chartData:
                del data['_id']
                chart.append(data)
            if date == lastDate:
                isNext = False
        return isNext, lastDate, chart

def update_chart(code, chart):
    collection = db['chart']
    for data in chart:
        update = data
        update['code'] = code
        collection.update_one({'code':code, 'date':data['date']}, {'$set':update}, upsert=True)






