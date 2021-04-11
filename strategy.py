import threading
import logging
import sys

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
        account_list = self.get_accountList()
        self.account_num = account_list[0]

        #QTest.qWait(10000)
        #self.kiwoom.screen_number_setting()

        self.saveAndCheck()
        # '005930' 삼성전자
        # '' 자리는 종목 코드가 들어가야 하나 빈 값으로 작성하면 종목이 아니라 주식 장의 시간 상태를 실시간으로 체크

    # account
    def get_accountList(self):
        accountList = models.get_accountList()
        if accountList is None:
            accountList = self.kiwoom.get_accountList()  # user No 확인
            models.update_accountList(accountList)
        self.logger.info('accountList: %s' % str(accountList))
        return accountList

    def get_accountInfo(self, account_num):
        isStockFinished = checkStockFinished()
        accountInfo = None
        if isStockFinished:
            accountInfo = models.get_accountInfo(account_num)
        if accountInfo is None:
            accountInfo = self.kiwoom.get_accountInfo(account_num)  # 예수금 상세현황 요청
            models.update_accountInfo(accountInfo)
        self.logger.info('account_lnfo: %s' %str(accountInfo))
        return accountInfo

    def get_myStock(self, account_num):
        profit, myStock = self.kiwoom.get_myStock(account_num)  # 계좌평가잔고내역 요청
        models.update_profit(account_num, profit)
        self.logger.info('profit : %s' %str(profit))
        models.update_myStock(account_num, myStock)
        self.logger.info('myStock : %s' %str(myStock))
        return profit, myStock

    def get_notSigned(self, account_num):
        notSigned = self.kiwoom.getNotSigned(account_num)
        self.logger.info('notSigned: %s' %str(notSigned))
        return notSigned

    # chart
    def gathering_daily_chart(self):
        self.logger.info('gathering daily chart')

        for market in self.market:
            codeList = self.kiwoom.get_codeList(market=self.market[market])

            for idx, code in enumerate(codeList):
                isStockFinished = checkStockFinished()
                if not isStockFinished:
                    break
                self.logger.info('%s/%s: %s stock code: %s is updating' %(idx, len(codeList), market, code))
                isNext, lastDate, chart = models.get_chart(code)
                if isNext:
                    recentChart = self.kiwoom.get_chart(type='daily', code=code, lastDate=lastDate)
                    chart = recentChart + chart
                    chart = self.addMovingAverage(chart)
                    recentChart = chart[0:len(recentChart)]
                    models.update_chart(recentChart)

    def addMovingAverage(self, chart):
        copy_chart = chart.copy()
        len_chart = len(chart)
        for idx in range(len_chart):
            total_price = 0
            if 'ma120' in chart[idx]:
                break
            for value in chart[idx:idx + 120]:
                total_price = total_price + value['close']
            copy_chart[idx]['ma120'] = int(total_price / len(chart[idx:idx + 120]))

            total_price = 0
            for value in chart[idx:idx + 20]:
                total_price = total_price + value['close']
            copy_chart[idx]['ma20'] = int(total_price / len(chart[idx:idx + 20]))
        return copy_chart

    # tatics
    def checkTatics(self):
        self.logger.info('check tatics')
        for market in self.market:
            codeList = self.kiwoom.get_codeList(market=self.market[market])
            for code in codeList:
                self.periodCheck(code=code)

    def periodCheck(self, isLast=True, code=None):
        _, _, chart = models.get_chart(code)
        if isLast:
            self.tatics(chart)
        else:
            len_chart = len(chart)
            for idx in range(len_chart):
                partChart = chart[idx:]
                self.tatics(partChart)

    def tatics(self, chart, targetPeriod=20):   # moving 이동 평균선, target 관심 영역의 기간
        # 그랜빌의 매매법칙중 4번째 매수 법칙
        is_ok = False
        if not chart or 'ma120' not in chart[0]:
            pass
        else:
            average_price = chart[0]['ma120']

            # 오늘자 주가가 120일 이평선에 걸쳐 있는지 확인
            bottom_stock_price = False
            high_price = None
            if chart[0]['low'] <= average_price and average_price <= chart[0]['high']:
                bottom_stock_price = True
                high_price = chart[0]['high']

            # 과거 일봉 데이터를 조회하면서 이동평균선보다 주가가 계속 밑에 존재하는지 확인
            prev_low_price = None
            prev_average_price = None
            if bottom_stock_price:
                price_top_moving = False
                len_chart = len(chart) - 1
                for i in range(len_chart):
                    idx = i + 1
                    prev_average_price = chart[idx]['ma120']
                    # target_period 동안 주가가 이동평균선보다 같거나 위에 있으면 조건 통과 못 함
                    if prev_average_price <= chart[idx]['high'] and idx <= targetPeriod:
                        price_top_moving = False
                        break
                    # target_period 전에 이평선 위에 있는 구간 존재
                    elif prev_average_price < chart[idx]['low'] and idx > targetPeriod:
                        self.logger.info('120일치 이평선 위에 있는 구간 확인됨')
                        price_top_moving = True
                        prev_low_price = chart[idx]['low']
                        break

                if price_top_moving:
                    if average_price > prev_average_price and high_price > prev_low_price:
                        is_ok = True
            if is_ok:
                self.logger.info('조건 통과')
                models.update_signal(chart[0]['code'], date=chart[0]['date'], type='granville', trade='buy', close=chart[0]['close'])

    # trigger
    def saveAndCheck(self):
        isStockFinished = checkStockFinished()

        if isStockFinished:
            if self.isFirstIn:
                #signed = self.kiwoom.get_signed(self.account_num)
                #print(signed)
                #pass
                self.get_accountInfo(self.account_num)
                self.get_myStock(self.account_num)
                '''not_signed_stock = self.get_not_signed_stock(self.account_num)
                self.isFirstIn = False
                self.isFirstOut = True'''
                self.gathering_daily_chart()
                self.checkTatics()
                self.logger.info('sys.exit')
                sys.exit()
            else:
                print(self.kiwoom.lastErrCode)
            t = threading.Timer(120, self.saveAndCheck)
        else:
            self.get_accountInfo(self.account_num)
            profit, myStock = self.get_myStock(self.account_num)
            # not_signed_stock = self.get_not_signed_stock(self.account_num)
            if self.isFirstOut:
                self.logger.info('실시간 data 수신')
                self.kiwoom.realdata('005930')
                self.isFirstOut = False
                self.isFirstIn = True
            else:
                trade = '신규매도'
                if myStock:
                    code = myStock[0]['code']
                    ordMsg = self.kiwoom.sendOrder(self.account_num, code, 1, 80000, trade)
                    self.logger.info(trade + str(ordMsg))
            #print('realStock', self.kiwoom.realStockData)
            t = threading.Timer(15, self.saveAndCheck)
        t.start()

    '''def checkTriggerAndOrder(self, account_num, code):
        if self.count % 1000 == 0:
            trade = '신규매수'
            self.kiwoom.order(account_num, code, 1, 85000, trade)
            if self.not_signed_stock:
                for orderNo in self.not_signed_stock:
                    code = self.not_signed_stock[orderNo]['종목코드']
                    quantity = self.not_signed_stock[orderNo]['미체결수량']
                    trade = self.not_signed_stock[orderNo]['주문구분']
                    if trade == '매수':
                        trade = '매수취소'
                        self.kiwoom.order(account_num, code, 0, 0, trade, orderNo=orderNo)
                    elif trade == '매도':
                        trade = '매도취소'
                        self.kiwoom.order(account_num, code, 0, 0, trade, orderNo=orderNo)
        elif self.count % 1000 == 500:
            print('stock_value', self.myStock)
            print('not_signed_stock', self.not_signed_stock)
            trade = '신규매도'
            self.kiwoom.order(account_num, code, 1, 80000, trade)
            if self.not_signed_stock:
                for orderNo in self.not_signed_stock:
                    code = self.not_signed_stock[orderNo]['종목코드']
                    quantity = self.not_signed_stock[orderNo]['미체결수량']
                    trade = self.not_signed_stock[orderNo]['주문구분']
                    if trade == '매수':
                        trade = '매수취소'
                        self.kiwoom.order(account_num, code, 0, 0, trade, orderNo=orderNo)
                    elif trade == '매도':
                        trade = '매도취소'
                        self.kiwoom.order(account_num, code, 0, 0, trade, orderNo=orderNo)
        self.count = self.count + 1'''




