import os
from kiwoom.kiwoom import *
from PyQt5.QtCore import *
import logging
import models
from datetime import datetime

class Strategy():
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info('strategy start')
        self.kiwoom = Kiwoom()

        # 기본 정보들
        self.market = {'코스피':'0', '코스닥':'10'}

        # condition 맞는 종목
        self.condition_stock_path = 'files/condition_stock.txt'

        # 변수
        self.account_info = None
        self.profit = None
        self.myStock = None
        self.not_signed_stock = None

        # 초기 세팅 함수들
        self.kiwoom.event_slots()       # 키움과 연결하기 위한 시그널 /슬롯 모음, login, trade, realdata
        self.kiwoom.login()             # 로그인 요청 함수

        account_list = self.get_account_list()
        account_num = account_list[0]
        self.get_account_info(account_num)
        self.get_my_stock(account_num)
        self.get_not_signed_stock(account_num)

        self.calculator_fnc()

        QTest.qWait(10000)
        self.read_code()
        self.kiwoom.screen_number_setting()

        QTest.qWait(5000)

        # 실시간 수신 관련 함수
        self.logger.info('실시간 data 수신')
        #self.kiwoom.realdata('005930')
        # '005930' 삼성전자
        # str(self.realType.REALTYPE['장시작시간']['장운영구분']), '0')
        # '' 자리는 종목 코드가 들어가야 하나 빈 값으로 작성하면 종목이 아니라 주식 장의 시간 상태를 실시간으로 체크크

    def get_account_list(self):
        account_list = models.get_account_list()
        if account_list is None:
            account_list = self.kiwoom.get_account_list()  # account No 확인
            models.update_account_list(account_list)
        self.logger.info('account_list: %s' % str(account_list))
        return account_list

    def get_account_info(self, account_num):
        self.account_info = models.get_account_info(account_num)
        if self.account_info is None:
            self.account_info = self.kiwoom.account_info(account_num)  # 예수금 상세현황 요청
            models.update_account_info(self.account_info)
        self.logger.info('account_lnfo: %s' %str(self.account_info))

    def get_my_stock(self, account_num):
        self.profit, self.myStock = self.kiwoom.get_myStock(account_num)  # 계좌평가잔고내역 요청
        models.update_profit(account_num, self.profit)
        self.logger.info('profit : %s' %str(self.profit))
        for code in self.myStock:
            models.update_myStock(account_num, code, self.myStock[code])
            self.logger.info('myStock : %s' %str(self.myStock[code]))

    def get_not_signed_stock(self, account_num):
        self.not_signed_stock = self.kiwoom.get_not_signed_stock(account_num)
        self.logger.info('not_signed_stock : %s' % str(self.not_signed_stock))

    def calculator_fnc(self):
        market_name = '코스닥'
        code_list = self.kiwoom.get_code_list(market=self.market[market_name])

        for idx, code in enumerate(code_list):
            self.kiwoom.disconnectRealData()
            self.logger.info('%s/%s : %s stock code: %s is updating' %(idx, len(code_list), market_name, code))
            isNext, lastDate, chart = models.get_chart(code)
            if isNext:
                recentChart = self.kiwoom.dailyChart(code=code, lastDate=lastDate)
                models.update_chart(code, recentChart)
                chart = recentChart + chart
            print('chart', len(chart))
            self.tatics(code=code, chart=chart)

    def tatics(self, code=None, chart=None, movingPeriod=120, targetPeriod=3):   # moving 이동 평균선, target 관심 영역의 기간
        # chart : date, o, h, l, c, v, t
        # 6 -> 3, 5 -> 2, 0 -> 4
        pass_success = False
        if chart is None or len(chart) < movingPeriod:
            pass_success = False
        else:
            total_price = 0
            for value in chart[:movingPeriod]:
                total_price = total_price + value['close']
            moving_average_price = total_price / movingPeriod

            bottom_stock_price = False
            current_high_price = None
            if chart[0]['low'] <= moving_average_price and moving_average_price <= chart[0]['high']: #low_price, high_price
                bottom_stock_price = True
                current_high_price = chart[0]['high']

            prev_low_price = None
            if bottom_stock_price:
                moving_average_price_prev = 0
                price_top_moving = False
                idx = 1

                while True:
                    if len(chart[idx:]) < movingPeriod:
                        self.logger.info('there is no data for the period: %s' %movingPeriod)
                        break

                    for value in chart[idx:movingPeriod + idx]:
                        total_price = total_price + value['close']
                    moving_average_price_prev = total_price / movingPeriod

                    if moving_average_price_prev <= int(chart[idx]['high']) and idx <= targetPeriod: # high price가 mvoing average 보다 높은 경우 fail
                        price_top_moving = False
                        break
                    elif (moving_average_price_prev < chart[idx]['low']) and idx > targetPeriod: # low price가 moving average 보다 높은 경구가 20일 전인 경우
                        self.logger.info('%s일치 이평선 위에 있는 구간 확인됨' %(movingPeriod))
                        price_top_moving = True
                        prev_low_price = chart[idx]['low']

                    idx = idx + 1

                if price_top_moving:
                    if moving_average_price > moving_average_price_prev and current_high_price > prev_low_price:
                        self.logger.info('이전 이평선 가격이 오늘자 이평선 가격보다 낮은 것 확인')
                        self.logger.info('이전 일봉 저가가 오늘자 일봉 고가보다 낮은지 확인')
                        pass_success = True

        if pass_success:
            self.logger.info('조건 통과')
            codeName = self.kiwoom.get_codeName(code)
            with open(self.condition_stock_path, 'a', encoding='utf-8') as f:
                f.write('%s\t%s\t현재가: %s\n' %(code, codeName, str(chart[0]['close'])))
                self.logger.info('%s\t%s\t현재가: %s\n' %(code, codeName, str(chart[0]['close'])))
        else:
            self.logger.info('조건 통과 못함')
            codeName = self.kiwoom.get_codeName(code)
            with open(self.condition_stock_path, 'a', encoding='utf-8') as f:
                f.write('%s\t%s\t현재가: %s\n' %(code, codeName, str(chart[0]['close'])))
                self.logger.info('%s\t%s\t현재가: %s\n' %(code, codeName, str(chart[0]['close'])))

    def read_code(self):
        if os.path.exists(self.condition_stock_path):
            with open(self.condition_stock_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    if line != '':
                        ls = line.split('\t')

                        code = ls[0]
                        code_nm = ls[1]
                        stock_price = int(ls[2].split('\n')[0])
                        self.kiwoom.portfolio.update({code:{'종목명':code_nm, '현재가':stock_price}})


