from werkzeug.security import check_password_hash
from views.config import page_default
from utils import paginate, getDate
from pymongo import MongoClient
import datetime

mongoClient = MongoClient('mongodb://localhost:27017/')
db = mongoClient['pytrade']

# users
def post_signUp(request_data):
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
def getAccountList():
    collection = db['account']
    data = collection.find_one({'accountList':{'$exists':'true'}})
    if data:
        return data['accountList']
    else:
        return data

def updateAccountList(accountList):
    collection = db['account']
    update = {'accountList':accountList}
    collection.update_one({'accountList': {'$exists':'true'}}, {'$set':update}, upsert=True)

def getAccountInfo(account, page=1, is_paging=False):
    collection = db['account']
    if is_paging:
        per_page = page_default['per_page']
        offset = (page - 1) * per_page
        data_list = collection.find({'account':account}, sort=[('date', -1)]).limit(per_page).skip(offset)
        count = data_list.count()
        paging = paginate(page, per_page, count)
        return paging, data_list
    else:
        date, _ = getDate()
        accountInfo = collection.find_one({'date':date, 'account':account})
        return accountInfo

def updateAccountInfo(update):
    collection = db['account']
    date, _ = getDate()
    update['date'] = date
    collection.update_one({'date':date, 'account':update['account']}, {'$set':update}, upsert=True)

def updateProfit(account, profit):
    collection = db['profit']
    date, _ = getDate()
    update = profit
    update['date'] = date
    update['account'] = account
    collection.update_one({'date':date, 'account':account}, {'$set':update}, upsert=True)

# code
def get_code(code=None, codeName=None):
    collection = db['code']
    data = None
    if codeName is not None and codeName != '':
        data = collection.find_one({'codeName':codeName})
    elif code is not None and code != '':
        data = collection.find_one({'code':code})
    return data

def update_code(update):
    collection = db['code']
    if 'codeName' in update and 'code' in update:
        collection.update_one({'codeName':update['codeName']}, {'$set':update}, upsert=True)
    else:
        pass

# mystock
def getMyStock(account, page=1, is_paging=False):
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

def updateMyStock(account, myStock):
    collection = db['stock']
    date, _ = getDate()
    for data in myStock:
        data['date'] = date
        data['account'] = account
        collection.update_one({'date':date, 'account':account, 'code':data['code']}, {'$set':data}, upsert=True)

def getChart(code, isJson=False, so='1year'):
    collection = db['chart']
    date, initialDate = getDate(so=so)
    chart = []
    if isJson:
        chartData = collection.find({'code':code, 'date':{'$gt':initialDate}}, sort=[('date', 1)])
        for data in chartData:
            del data['_id']
            chart.append(data)
        return chart
    else:
        isNext = True
        lastDate = None
        lastChart = collection.find_one({'code':code}, sort=[('date', -1)])
        if lastChart is not None:
            lastDate = lastChart['date']
            chartData = collection.find({'code':code, 'date':{'$gt':initialDate}}, sort=[('date', -1)])
            for data in chartData:
                del data['_id']
                chart.append(data)
            if date == lastDate:
                isNext = False
        return isNext, lastDate, chart

def updateChart(chart, so='5year'):
    collection = db['chart']
    date, initialDate = getDate(so=so)
    initialDate = int(initialDate)
    for data in chart:
        if int(data['date']) < initialDate:
            break
        else:
            collection.update_one({'code':data['code'], 'date':data['date']}, {'$set':data}, upsert=True)

# signal
def getSignal(page=1, codeName=None, so='1year', is_paging=False):
    date, initialDate = getDate(so=so)
    collection = db['signal']
    if is_paging:
        per_page = page_default['per_page']
        offset = (page - 1) * per_page
        if codeName is None:
            data_list = collection.find({'date':{'$gt':initialDate}}, sort=[('date', -1)]).limit(per_page).skip(offset)
        else:
            data_list = collection.find({'codeName':codeName, 'date':{'$gt':initialDate}}, sort=[('date', -1)]).limit(per_page).skip(offset)
        count = data_list.count()
        paging = paginate(page, per_page, count)
        return paging, data_list
    else:
        date, initialDate = getDate()
        data_list = collection.find({'date':date})
        return data_list

def updateSignal(code, date=None, type=None, trade=None, close=None):
    if date is None or type is None or trade is None or close is None:
        pass
    else:
        data = get_code(code)
        if data:
            collection = db['signal']
            codeName = data['codeName']
            update = {'code':code, 'codeName':codeName, 'date':date, 'type':type, 'trade':trade, 'close':close}
            collection.update_one({'code':code, 'date':date, 'type':type}, {'$set':update}, upsert=True)

def getChartSignal(code, type='granville', so='1year'):
    date, initialDate = getDate(so=so)

    collection = db['signal']
    signals = collection.find({'code':code, 'type':type, 'date':{'$gt':initialDate}}, sort=[('date', 1)])
    signalDict = {}
    for signal in signals:
        del signal['_id']
        signalDict[signal['date']] = signal

    collection = db['chart']
    chartData = collection.find({'code':code, 'date':{'$gt':initialDate}}, sort=[('date', 1)])
    chart = []
    buySignals = []
    sellSignals = []
    for idx, data in enumerate(chartData):
        del data['_id']
        chart.append({'x':idx, 'date':data['date'], 'close':data['close'], 'ma120':data['ma120'], 'ma20':data['ma20'], 'std20':data['std20']})
        if data['date'] in signalDict:
            if signalDict[data['date']]['trade'] == 'buy':
                buySignals.append({'x':idx, 'close':data['close']})
            elif signalDict[data['date']]['trade'] == 'sell':
                sellSignals.append({'x':idx, 'close':data['close']})
    return chart, buySignals, sellSignals

# 실시간
def updateTick(request_data):
    collection = db['trade']
    request_data = request_data
    collection.insert_one(request_data)

def updateOrderBook(request_data):
    collection = db['orderbook']
    request_data = request_data
    collection.insert_one(request_data)

# revised
def revisedPrice(code=None, date=None, ratio=1):
    collection = db['chart']
    afterData = collection.find({'code':code, 'date':{'$gte':date}}, sort=[('date', -1)])
    beforeData = collection.find({'code':code, 'date':{'$lt':date}}, sort=[('date', -1)])
    revised_chart = []

    isRevised = True
    for data in afterData:
        del data['_id']
        revised_chart.append(data)
    i = 0
    for data in beforeData:
        copyData = data.copy()
        if i == 0:
            if revised_chart[-1]['close'] < data['close'] * 1.3 and revised_chart[-1]['close'] > data['close'] * 0.7:
                isRevised = False
                break
        del copyData['_id']
        copyData['high'] = int(copyData['high'] / ratio)
        copyData['open'] = int(copyData['open'] / ratio)
        copyData['low'] = int(copyData['low'] / ratio)
        copyData['close'] = int(copyData['close'] / ratio)
        copyData['volume'] = int(copyData['volume'] * ratio)
        revised_chart.append(copyData)
        i = i + 1

    if isRevised:
        len_chart = len(revised_chart)
        chart = revised_chart.copy()
        for idx in range(len_chart):
            total_price = 0
            for value in chart[idx:idx + 120]:
                total_price = total_price + value['close']
            chart[idx]['ma120'] = int(total_price / len(chart[idx:idx + 120]))

            total_price = 0
            for value in chart[idx:idx + 20]:
                total_price = total_price + value['close']
            chart[idx]['ma20'] = int(total_price / len(chart[idx:idx + 20]))

        for data in chart:
            collection.update_one({'code':data['code'], 'date':data['date']}, {'$set':data}, upsert=True)

        collection = db['signal']
        collection.delete_many({'code':code})







