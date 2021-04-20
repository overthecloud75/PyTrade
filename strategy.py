import threading
import logging
import sys
import math
import time

from kiwoom.kiwoom import *
import models
from utils import checkStockFinished

class Strategy():
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info('strategy start')
        self.kiwoom = Kiwoom()

        # 변수
        self.isFirstIn = True
        self.isFirstOut = True

        # 기본 정보들
        self.market = {'코스피':'0', '코스닥':'10'}

        # 초기 세팅 함수들
        self.kiwoom.login()             # 로그인 요청 함수

        # account 정보 수집
        accountList = self.getAccountList()
        self.accountNum = accountList[0]

        #QTest.qWait(10000)
        #self.kiwoom.screen_number_setting()

        self.saveAndCheck()
        # '005930' 삼성전자
        # '' 자리는 종목 코드가 들어가야 하나 빈 값으로 작성하면 종목이 아니라 주식 장의 시간 상태를 실시간으로 체크

    # account
    def getAccountList(self):
        accountList = models.getAccountList()
        if accountList is None:
            accountList = self.kiwoom.getAccountList()  # user No 확인
            models.updateAccountList(accountList)
        self.logger.info('accountList: %s' % str(accountList))
        return accountList

    def getAccountInfo(self, accountNum):
        isStockFinished = checkStockFinished()
        accountInfo = None
        if isStockFinished:
            accountInfo = models.getAccountInfo(accountNum)
        if accountInfo is None:
            accountInfo = self.kiwoom.getAccountInfo(accountNum)  # 예수금 상세현황 요청
            models.updateAccountInfo(accountInfo)
        self.logger.info('accountInfo: %s' %str(accountInfo))
        return accountInfo

    def getMyStock(self, accountNum):
        profit, myStock = self.kiwoom.getMyStock(accountNum)  # 계좌평가잔고내역 요청
        models.updateProfit(accountNum, profit)
        self.logger.info('profit : %s' %str(profit))
        models.updateMyStock(accountNum, myStock)
        self.logger.info('myStock : %s' %str(myStock))
        return profit, myStock

    def getNotSigned(self, accountNum):
        notSigned = self.kiwoom.getNotSigned(accountNum)
        self.logger.info('notSigned: %s' %str(notSigned))
        return notSigned

    # chart
    def gatheringDailyChart(self):
        self.logger.info('gathering daily chart')

        for market in self.market:
            codeList = self.kiwoom.getCodeList(market=self.market[market])

            for idx, code in enumerate(codeList):
                isStockFinished = checkStockFinished()
                if not isStockFinished:
                    break
                self.logger.info('%s/%s: %s stock code: %s is updating' %(idx, len(codeList), market, code))
                isNext, lastDate, chart = models.getChart(code)
                if isNext:
                    recentChart = self.kiwoom.getChart(type='daily', code=code, lastDate=lastDate)
                    chart = recentChart + chart
                    chart = self.addMoving(chart)
                    models.updateChart(chart)

    def addMoving(self, chart):
        copyChart = chart.copy()
        lenChart = len(chart)
        chartSize = 0
        for idx in range(lenChart):
            if 'ma120' in chart[idx]:
                chartSize = idx
                break
            totalPrice = 0
            for value in chart[idx:idx + 120]:
                totalPrice = totalPrice + value['close']
            copyChart[idx]['ma120'] = int(totalPrice / len(chart[idx:idx + 120]))

            vsum = 0
            for value in chart[idx:idx + 120]:
                vsum = vsum + (value['close'] - copyChart[idx]['ma120']) ** 2
            copyChart[idx]['std120'] = round(math.sqrt(vsum / len(chart[idx:idx + 120])), 2)

            totalPrice = 0
            for value in chart[idx:idx + 20]:
                totalPrice = totalPrice + value['close']
            copyChart[idx]['ma20'] = int(totalPrice / len(chart[idx:idx + 20]))

            vsum = 0
            for value in chart[idx:idx + 20]:
                vsum = vsum + (value['close'] - copyChart[idx]['ma20']) ** 2
            copyChart[idx]['std20'] = round(math.sqrt(vsum / len(chart[idx:idx + 20])), 2)
        copyChart = copyChart[:chartSize]
        return copyChart

    # tatics
    def checkTatics(self):
        self.logger.info('check tatics')
        for market in self.market:
            codeList = self.kiwoom.getCodeList(market=self.market[market])
            for code in codeList:
                self.periodCheck(period=500000, code=code, so='5year')

    def periodCheck(self, period=None, code=None, so='1year'):
        _, _, chart = models.getChart(code, so=so)
        if period is None:
            self.tatics(chart)
        else:
            lenChart = len(chart)
            for idx in range(lenChart):
                if idx >= period:
                    break
                partChart = chart[idx:]
                self.tatics(partChart)

    def tatics(self, chart, targetPeriod=20):   # moving 이동 평균선, target 관심 영역의 기간
        # 그랜빌의 매매법칙중 4번째 매수 법칙
        if not chart or 'ma120' not in chart[0]:
            pass
        else:
            ma120Price = chart[0]['ma120']
            ma20Price = chart[0]['ma20']
            std20 = chart[0]['std20']
            lenChart = len(chart) - 1

            type = 'granville'
            highPrice = chart[0]['high']
            closePrice = chart[0]['close']

            # 오늘자 주가가 120일 이평선에 걸쳐 있는지 확인
            if chart[0]['low'] <= ma120Price and ma120Price <= highPrice:
                for i in range(lenChart):
                    idx = i + 1
                    prevMa120Price = chart[idx]['ma120']
                    # target period 동안 주가가 이동평균선보다 같거나 위에 있으면 조건 통과 못 함
                    if prevMa120Price <= chart[idx]['high'] and idx <= targetPeriod:
                        break
                    # target period 전에 이평선 위에 있는 구간 존재
                    elif prevMa120Price < chart[idx]['low'] and idx > targetPeriod:
                        self.logger.info('120일치 이평선 위에 있는 구간 확인됨')
                        prevLowPrice = chart[idx]['low']
                        # ma120및 price값이 prev 보다 상승
                        if ma120Price > prevMa120Price and highPrice > prevLowPrice:
                            self.logger.info('조건 통과')
                            models.updateSignal(chart[0]['code'], date=chart[0]['date'], type=type, trade='buy', close=closePrice)
                        break

            type = 'ma'
            if ma120Price < ma20Price:
                for i in range(lenChart):
                    idx = i + 1
                    prevMa120Price = chart[idx]['ma120']
                    prevMa20Price = chart[idx]['ma20']
                    # target period 동안 20일 이동 주가가 이동평균선보다 같거나 위에 있으면 조건 통과 못 함
                    if prevMa120Price < prevMa20Price and idx <= targetPeriod:
                        break
                        # target period 전에 이평선 위에 있는 구간 존재
                    elif prevMa120Price < prevMa20Price and idx > targetPeriod:
                        # self.logger.info('120일치 이평선 위에 있는 구간 확인됨')
                        # ma120및 price값이 prev 보다 상승
                        if ma120Price > prevMa120Price:
                            self.logger.info('조건 통과')
                            models.updateSignal(chart[0]['code'], date=chart[0]['date'], type=type, trade='buy', close=closePrice)
                        break
            elif ma120Price > ma20Price:
                for i in range(lenChart):
                    idx = i + 1
                    prevMa120Price = chart[idx]['ma120']
                    prevMa20Price = chart[idx]['ma20']
                    # target period 동안 20일 이동 주가가 이동평균선보다 같거나 아래에 있으면 조건 통과 못 함
                    if prevMa120Price > prevMa20Price and idx <= targetPeriod:
                        break
                        # target period 전에 이평선 아래에 있는 구간 존재
                    elif prevMa120Price > prevMa20Price and idx > targetPeriod:
                        # self.logger.info('120일치 이평선 위에 있는 구간 확인됨')
                        # ma120및 price값이 prev 보다 하락
                        if ma120Price < prevMa120Price:
                            self.logger.info('조건 통과')
                            models.updateSignal(chart[0]['code'], date=chart[0]['date'], type=type, trade='sell', close=closePrice)
                        break

            type = 'bollinger'
            if closePrice < ma20Price - 2 * std20:
                models.updateSignal(chart[0]['code'], date=chart[0]['date'], type=type, trade='buy', close=closePrice)
            elif closePrice > ma20Price + 2 * std20:
                models.updateSignal(chart[0]['code'], date=chart[0]['date'], type=type, trade='sell', close=closePrice)

    def revised(self, code=None, date=None, ratio=1):
        models.revisedPrice(code=code, date=date, ratio=ratio)
        self.periodCheck(period=20000, code=code, so='5year')

    # trigger
    def saveAndCheck(self):
        isStockFinished = checkStockFinished()

        if isStockFinished:
            if self.isFirstIn:
                signed = self.kiwoom.getSigned(self.accountNum)
                #print(signed)
                self.getAccountInfo(self.accountNum)
                self.getMyStock(self.accountNum)
                '''notSigned = self.getNotSigned(self.accountNum)
                self.isFirstIn = False
                self.isFirstOut = True'''
                #self.gatheringDailyChart()
                self.checkTatics()
                self.logger.info('sys.exit')
                sys.exit()
            else:
                print(self.kiwoom.lastErrCode)
            t = threading.Timer(120, self.saveAndCheck)
        else:
            self.getAccountInfo(self.accountNum)
            profit, myStock = self.getMyStock(self.accountNum)
            # notSigned = self.getNotSigned(self.accountNum)
            if self.isFirstOut:
                self.logger.info('실시간 data 수신')
                self.kiwoom.realdata('001510')
                self.isFirstOut = False
                self.isFirstIn = True
            else:
                trade = '신규매도'
                if myStock:
                    code = myStock[0]['code']
                    ordMsg = self.kiwoom.sendOrder(self.accountNum, code, 1, 80000, trade)
                    self.logger.info(trade + str(ordMsg))
            timestamp = int(time.time())
            tradeData = {'timestamp':timestamp, 'data':self.kiwoom.tradeData.copy()}
            orderbook = {'timestamp':timestamp, 'data':self.kiwoom.orderBook.copy()}
            self.kiwoom.tradeData['BuyQty'] = 0
            self.kiwoom.tradeData['SellQty'] = 0
            models.updateTick(tradeData)
            models.updateOrderBook(orderbook)
            t = threading.Timer(15, self.saveAndCheck)
        t.start()

    '''def checkTriggerAndOrder(self, accountNum, code):
        if self.count % 1000 == 0:
            trade = '신규매수'
            self.kiwoom.order(accountNum, code, 1, 85000, trade)
            if self.notSigned:
                for ordNo in self.notSigned:
                    code = self.notSigned[ordNo]['종목코드']
                    quantity = self.notSigned[ordNo]['미체결수량']
                    trade = self.notSigned[ordNo]['주문구분']
                    if trade == '매수':
                        trade = '매수취소'
                        self.kiwoom.order(accountNum, code, 0, 0, trade, ordNo=ordNo)
                    elif trade == '매도':
                        trade = '매도취소'
                        self.kiwoom.order(accountNum, code, 0, 0, trade, ordNo=ordNo)
        elif self.count % 1000 == 500:
            print('stockvalue', self.myStock)
            print('notSigned', self.notSigned)
            trade = '신규매도'
            self.kiwoom.order(accountNum, code, 1, 80000, trade)
            if self.notSigned:
                for ordNo in self.notSigned:
                    code = self.notSigned[ordNo]['종목코드']
                    quantity = self.notSigned[ordNo]['미체결수량']
                    trade = self.notSigned[ordNo]['주문구분']
                    if trade == '매수':
                        trade = '매수취소'
                        self.kiwoom.order(accountNum, code, 0, 0, trade, ordNo=ordNo)
                    elif trade == '매도':
                        trade = '매도취소'
                        self.kiwoom.order(accountNum, code, 0, 0, trade, ordNo=ordNo)
        self.count = self.count + 1'''




