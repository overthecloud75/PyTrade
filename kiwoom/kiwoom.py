from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import QTest
import pythoncom
from config.errorCode import *
from config.kiwoomType import *
import logging

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info('Kiwoom class start')

        self.realType = RealType()

        # 계좌 관련된 변수
        self.profit = {}
        self.myStock = {}
        self.not_signed_stock = {}
        self.account_num = None
        self.account_secret = '0000'
        self.deposit = 0  # 예수금
        self.use_money = 0  # 실제 투자에 사용할 금액
        self.use_money_percent = 0.5 # 예수금에서 실제 사용할 비율
        self.output_deposit = 0

        # pythoncom
        self.block = False
        self.received = False

        # 종목 분석 용
        self.chart = []
        self.count = 0

        # condition 맞는 종목
        self.portfolio = {}

        # 요청 스크린 번호
        self.screen_my_info = '2000' # 계좌 관련한 스크린 번호
        self.screen_calculation_stock = '4000'
        self.screen_real_stock = '5000'
        self.screen_meme_stock = '6000'
        self.screen_start_stop_real = '1000' # 장 시작/종료 실시간 스크린 번호

       # 초기 세팅 함수들
        self.get_ocx_instance()  # OCX 방식을 파이썬에 사용할 수 있게 변환해 주는 함수

    def get_ocx_instance(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')  # ocx 확장자도 파이썬에서 사용할 수 있게 해 준다.
                                                      # registery에 저장된 API 모듈 불러오기
    def GetCommData(self, trcode, rqname, index, item):
        data = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, index, item)
        return data.strip()

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.tradata_slot)
        self.OnReceiveRealData.connect(self.realdata_slot)

    def login(self):
        self.dynamicCall('CommConnect()')   # dynamicCall은 pyQt5에서 제공하는 함수로 서버에 데이터를 송수신해 주는 역할을 함
        self.block = False
        while not self.block:
            pythoncom.PumpWaitingMessages()

    def login_slot(self, err_code):
        self.logger.info(errors(err_code))
        self.block = True

    def tradata_slot(self, sScrNo, rqname, trcode, sRecordName, isNext):
        if rqname == '예수금상세현황요청':
            deposit = self.GetCommData(trcode, rqname, 0, '예수금')
            output_deposit = self.GetCommData(trcode, rqname, 0, '출금가능금액')

            self.deposit = int(deposit)
            self.use_money = float(self.deposit) * self.use_money_percent / 4
            self.output_deposit = int(output_deposit)

            self.stop_screen_cancel(self.screen_my_info)
            self.block = True

        elif rqname == '계좌평가잔고내역요청':
            buy_money = self.GetCommData(trcode, rqname, 0, '총매입금액')
            loss_money = self.GetCommData(trcode, rqname, 0, '총평가손익금액')
            loss_rate = self.GetCommData(trcode, rqname, 0, '총수익률(%)')
            self.profit['총매입금액'] = int(buy_money)
            self.profit['총평가손익금액'] = int(loss_money)
            self.profit['총수익률(%)'] = float(loss_rate)

            rows = self.dynamicCall('GetRepeatCnt(Qstring, Qstring)', trcode, rqname)
            for i in range(rows):
                code = self.GetCommData(trcode, rqname, i, '종목번호')
                code_name = self.GetCommData(trcode, rqname, i, '종목명')
                stock_quantity = self.GetCommData(trcode, rqname, i, '보유수량')
                buy_price = self.GetCommData(trcode, rqname, i, '매입가')
                earn_late = self.GetCommData(trcode, rqname, i, '수익률(%)')
                current_price = self.GetCommData(trcode, rqname, i, '현재가')
                total_exec_price = self.GetCommData(trcode, rqname, i, '매입금액')
                possible_quantity = self.GetCommData(trcode, rqname, i, '매매가능수량')

                code = code[1:]
                if code in self.myStock:
                    pass
                else:
                    self.myStock[code] = {}

                self.myStock[code]['종목명'] = code_name
                self.myStock[code]['보유수량'] =  int(stock_quantity)
                self.myStock[code]['매입가'] = int(buy_price)
                self.myStock[code]['수익률'] = float(earn_late)
                self.myStock[code]['현재가'] = int(current_price)
                self.myStock[code]['매입금액'] = int(total_exec_price)
                self.myStock[code]['매매가능수량'] = int(possible_quantity)

            if isNext == '2':
                self.get_myStock(isNext='2')
            else:
                self.stop_screen_cancel(self.screen_my_info)
                self.block = True

        elif rqname == '실시간미체결요청':
            rows = self.dynamicCall('GetRepeatCnt(Qstring, Qstring)', trcode, rqname)
            for i in range(rows):
                code = self.GetCommData(trcode, rqname, i, '종목코드')
                code_name = self.GetCommData(trcode, rqname, i, '종목명')
                order_no = self.GetCommData(trcode, rqname, i, '주문번호')
                order_status = self.GetCommData(trcode, rqname, i, '주문상태')
                order_quantity = self.GetCommData(trcode, rqname, i, '주문수량')
                order_price = self.GetCommData(trcode, rqname, i, '주문가격')
                order_type = self.GetCommData(trcode, rqname, i, '주문구분')
                not_quantity = self.GetCommData(trcode, rqname, i, '미체결수량')
                ok_quantity = self.GetCommData(trcode, rqname, i, '체결량')

                order_no = int(order_no)
                if order_no in self.not_signed_stock:
                    pass
                else:
                    self.not_signed_stock[order_no] = {}

                self.not_signed_stock[order_no]['종목코드'] = code
                self.not_signed_stock[order_no]['종목명'] =  code_name
                self.not_signed_stock[order_no]['주문상태'] = order_status
                self.not_signed_stock[order_no]['주문수량'] = int(order_quantity)
                self.not_signed_stock[order_no]['주문가격'] = int(order_price)
                self.not_signed_stock[order_no]['주문구분'] = order_type.lstrip('+').lstrip('-')
                self.not_sigend_stock[order_no]['미체결수량'] = int(not_quantity)
                self.not_signed_stock[order_no]['미체결량'] = int(ok_quantity)

            if isNext == '2':
                self.get_not_signed_stock(isNext='2')
            else:
                self.stop_screen_cancel(self.screen_my_info)
                self.block = True
                self.logger.info(rqname + ' 종료')

        elif rqname == '주식일봉차트조회':
            isLast = False
            code = self.GetCommData(trcode, rqname, 0, '종목코드')
            cnt = self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, rqname)

            for i in range(cnt):
                date = self.GetCommData(trcode, rqname, i, '일자')
                open = self.GetCommData(trcode, rqname, i, '시가')
                high = self.GetCommData(trcode, rqname, i, '고가')
                low = self.GetCommData(trcode, rqname, i, '저가')
                close = self.GetCommData(trcode, rqname, i, '현재가')
                volume = self.GetCommData(trcode, rqname, i, '거래량')
                trading = self.GetCommData(trcode, rqname, i, '거래대금')
                if date == self.lastDate:
                    isLast = True
                    break
                data = {'date':date, 'open':int(open), 'high':int(high), 'low':int(low), 'close':int(close), 'volume':int(volume), 'trading':int(trading)}
                self.chart.append(data.copy())

            if not isLast:
                if isNext == '2':
                    self.dailyData(code=code, isNext=isNext)
                else:
                    self.block = True
            else:
                self.block = True

    def realdata(self, scode):
        self.dynamicCall('SetRealReg(QString, QString, QString, QString)',
                         self.screen_start_stop_real, scode, '20', '0')

    def disconnectRealData(self):
        self.dynamicCall('DisconnectRealData(QString)', self.screen_calculation_stock)

    def realdata_slot(self, sCode, sRealType, sRealData):

        if sRealType == '장시작시간':
            self.logger.info('장시작시간')
            fid = self.realType.REALTYPE[sRealType]['장운영구분'] # (0:장시작전, 2:장종료전, 3:장시작)
            value = self.dynamicCall('GetCommRealData(QString, int)', sCode, fid)
            fid_mean = None
            if value == '0':
                fid_mean = '장시작 전'
            elif value == '3':
                fid_mean = '장시작'
            elif value == '2':
                fid_mean = '장종료, 동시호가로 넘어감 '
            elif value == '4':
                fid_mean = '3시간30분 장 종료'
            self.logger.info('%s: %s'%(sRealType, fid_mean))

        elif sRealType == '주식체결':
            date = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['체결시간'])
            current_price = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['현재가'])
            compared = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['전일대비'])
            fluctuation = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['등락율'])
            ask = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['(최우선)매도호가'])
            bid = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['(최우선)매수호가'])
            quantity = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['거래량'])
            value = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['누적거래량'])
            high_price = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['고가'])
            start_price = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['시가'])
            low_price = self.dynamicCall('GetCommRealData(QString, int)', sCode, self.realType.REALTYPE[sRealType]['저가'])

            real_data = {'체결시간':date, '현재가':int(current_price), '전일대비':int(compared), '등락률':float(fluctuation),
                         '(최우선)매도호가':abs(int(ask)), '(최우선)매수호가':abs(int(bid)), '거래량':int(quantity), '누적거래량':abs(int(value)),
                         '고가':int(high_price), '시가':int(start_price), '저가':int(low_price)}
            if sCode not in self.portfolio:
                self.portfolio[sCode] = real_data
            else:
                self.portfolio[sCode].update(real_data)
            self.checkTriggerAndOrder(sCode)

    def stop_screen_cancel(self, sScrNo=None):
        self.dynamicCall('DisconnectRealData(QString)', sScrNo)

    def get_account_list(self):
        account_list = self.dynamicCall('GetLoginInfo(QString)', 'ACCNO')
        account_list = account_list.split(';')[:-1]
        return account_list

    def account_info(self, account_num, isNext='0'):
        sRQName = '예수금상세현황요청'
        self.account_num = account_num
        self.logger.info(sRQName)
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호', self.account_secret)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(QString, QString)', '조회구분', '3')
        self.dynamicCall('CommRqData(QString, QString, int, QString)', sRQName, 'opw00001', isNext, self.screen_my_info)

        self.block = False
        while not self.block:
            pythoncom.PumpWaitingMessages()
        return {'account':account_num, '예수금':self.deposit, '출금가능금액':self.output_deposit}

    def get_myStock(self, account_num, isNext='0'):
        sRQName = '계좌평가잔고내역요청'
        self.account_num = account_num
        self.logger.info(sRQName)
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호', self.account_secret)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(QString, QString)', '조회구분', '1')
        self.dynamicCall('CommRqData(QString, QString, int, QString)', sRQName, 'opw00018', isNext, self.screen_my_info)

        self.block = False
        i = 0
        while not self.block:
            pythoncom.PumpWaitingMessages()
        return self.profit, self.myStock

    def get_not_signed_stock(self, account_num, isNext='0'):
        sRQName = '실시간미체결요청'
        self.account_num = account_num
        self.logger.info(sRQName)
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '매매구분', '0') # 매매구분 = 0:전체, 1:매도, 2:매수
        self.dynamicCall('SetInputValue(QString, QString)', '체결구분', '1') # 체결구분 = 0:전체, 2:체결, 1:미체결
        self.dynamicCall('CommRqData(QString, QString, int, QString)', sRQName, 'opt10075', isNext, self.screen_my_info)

        self.block = False
        while not self.block:
            pythoncom.PumpWaitingMessages()
        return self.not_signed_stock

    def get_code_list(self, market='0'):
        code_list = self.dynamicCall('GetCodeListByMarket(QString)', market)
        code_list = code_list.split(';')[:-1]
        return code_list

    def get_codeName(self, code):
        codeName = self.dynamicCall('GetMasterCodeName(QString)', code)
        return codeName

    def dailyChart(self, code=None, lastDate=None):
        self.block = False
        self.chart = []
        self.lastDate = lastDate
        self.dailyData(code=code)
        while not self.block:
            pythoncom.PumpWaitingMessages()
        self.lastDate = None
        return self.chart

    def dailyData(self, code=None, date=None, isNext='0'):
        QTest.qWait(5000)
        self.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
        self.dynamicCall('SetInputValue(QString, QString)', '수정주가부분', '1')
        if date is not None:
            self.dynamicCall('SetInputValue(QString, QString)', '기준일자', date)
        self.dynamicCall('CommRqData(QString, QString, int, QString)', '주식일봉차트조회', 'opt10081', isNext, self.screen_calculation_stock)

    def screen_number_setting(self):
        screen_overwrite = []

        # 계좌평가잔고내역에 있는 종목들
        for code in self.myStock:
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for order_number in self.not_signed_stock:
            code = self.not_signed_stock[order_number]['종목코드']

            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 포트폴리오에 있는 종목들
        for code in self.portfolio:
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 스크린 번호 할당
        cnt = 0
        for code in screen_overwrite:
            real_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)
            if (cnt%50) == 0:
                real_screen = real_screen + 1
                meme_screen = meme_screen + 1
                self.screen_real_stock = str(real_screen)
                self.screen_meme_stock = str(meme_screen)

            if code in self.portfolio:
                self.portfolio[code]['스크린번호'] = self.screen_real_stock
                self.portfolio[code]['주문용스크린번호'] = self.screen_meme_stock
            else:
                self.portfolio[code]= {'스크린번호':self.screen_real_stock, '주문용스크린번호':self.screen_meme_stock}

            cnt = cnt + 1

    def checkTriggerAndOrder(self, scode):
        if self.count % 1000 == 0:
            print('stock_value', self.myStock)
            print('not_signed_stock', self.not_signed_stock)
            print('portfolio', self.portfolio)
            trade = '신규매수'
            #self.order(scode, 1, 85000, trade)
            if self.not_signed_stock:
                for orderNo in self.not_signed_stcok:
                    scode = self.not_signed_stock[orderNo]['종목코드']
                    quantity = self.not_signed_stock[orderNo]['미체결수량']
                    trade = self.not_signed_stock[orderNo]['주문구분']
                    if trade == '매수':
                        trade = '매수취소'
                        self.order(scode, 0, 0, trade, orderNo=orderNo)
                    elif trade == '매도':
                        trade = '매도취소'
                        self.order(scode, 0, 0, trade, orderNo=orderNo)
        elif self.count % 1000 == 500:
            print('stock_value', self.myStock)
            print('not_signed_stock', self.not_signed_stock)
            print('portfolio', self.portfolio)
            trade = '신규매도'
            #self.order(scode, 1, 80000, trade)
            if self.not_signed_stock:
                for orderNo in self.not_signed_stcok:
                    scode = self.not_signed_stock[orderNo]['종목코드']
                    quantity = self.not_signed_stock[orderNo]['미체결수량']
                    trade = self.not_signed_stock[orderNo]['주문구분']
                    if trade == '매수':
                        trade = '매수취소'
                        self.order(scode, 0, 0, trade, orderNo=orderNo)
                    elif trade == '매도':
                        trade = '매도취소'
                        self.order(scode, 0, 0, trade, orderNo=orderNo)
        self.count = self.count + 1

    def order(self, sCode, quantity, price, trade, orderType='지정가', orderNo=''):
        order = [trade, self.screen_meme_stock, self.account_num, self.realType.SENDTYPE['trade'][trade],
                 sCode, quantity, price, self.realType.SENDTYPE['orderType'][orderType], orderNo]
        self.logger.info('SendOrder : %s'%str(order))
        order_msg = self.dynamicCall('SendOrder(QString, QString, QString, int, QSting, int, int, QString, QString)',order)
        if order_msg:
            self.logger.info(order_msg)
            self.logger.info(trade + '전달 성공')
        else:
            self.logger.info(trade + '전달 실패')






