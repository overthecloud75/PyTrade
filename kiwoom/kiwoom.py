from PyQt5.QAxContainer import *
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

        # errorCode
        self.lastErrCode = None

        # 계좌 관련된 변수
        self.profit = {}
        self.myStock = []
        self.not_signed_stock = {}
        self.account_secret = '0000'
        self.deposit = 0  # 예수금
        self.output_deposit = 0

        # pythoncom
        self.block = True

        # realData
        self.realStockData = {}

        # 요청 스크린 번호
        self.screen_myInfo = '2000' # 계좌 관련한 스크린 번호
        self.screen_chart = '4000'
        self.screen_real = '5000'
        self.screen_meme = '6000'
        self.screen_start_stop_real = '1000' # 장 시작/종료 실시간 스크린 번호

       # 초기 세팅 함수들
        self.get_ocx_instance()  # OCX 방식을 파이썬에 사용할 수 있게 변환해 주는 함수
        self.event_slots()  # 키움과 연결하기 위한 시그널 /슬롯 모음, login, trade, realdata

    def get_ocx_instance(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')  # ocx 확장자도 파이썬에서 사용할 수 있게 해 준다.
                                                      # registery에 저장된 API 모듈 불러오기

    # dynamicCall
    def SetInputValue(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def CommRqData(self, rqname, trcode, next, screen):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen)

    def GetCommData(self, trcode, rqname, index, item):
        data = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, index, item)
        return data.strip()

    def GetCommRealData(self, code, fid):
        data = self.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return data

    def disconnectRealData(self):
        self.dynamicCall('DisconnectRealData(QString)', self.screen_chart)

    def stop_screen(self, sScrNo=None):
        self.dynamicCall('DisconnectRealData(QString)', sScrNo)

    # slots
    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.tradata_slot)
        self.OnReceiveRealData.connect(self.realdata_slot)

    def login_slot(self, errCode):
        self.logger.info('login status: %s' %errors(errCode))
        self.lastErrCode = errCode
        self.block = False

    def tradata_slot(self, sScrNo, rqname, trcode, sRecordName, next):
        if rqname == '예수금상세현황요청':
            deposit = self.GetCommData(trcode, rqname, 0, '예수금')
            output_deposit = self.GetCommData(trcode, rqname, 0, '출금가능금액')

            self.deposit = int(deposit)
            self.output_deposit = int(output_deposit )

            self.stop_screen(self.screen_myInfo)
            self.block = False

        elif rqname == '계좌평가잔고내역요청':
            buy_money = self.GetCommData(trcode, rqname, 0, '총매입금액')
            loss_money = self.GetCommData(trcode, rqname, 0, '총평가손익금액')
            loss_rate = self.GetCommData(trcode, rqname, 0, '총수익률(%)')
            self.profit['총매입금액'] = int(buy_money)
            self.profit['총평가손익금액'] = int(loss_money)
            self.profit['총수익률(%)'] = float(loss_rate)

            self.myStock = []
            rows = self.dynamicCall('GetRepeatCnt(Qstring, Qstring)', trcode, rqname)
            for i in range(rows):
                code = self.GetCommData(trcode, rqname, i, '종목번호')
                codeName = self.GetCommData(trcode, rqname, i, '종목명')
                stock_quantity = self.GetCommData(trcode, rqname, i, '보유수량')
                buy_price = self.GetCommData(trcode, rqname, i, '매입가')
                earn_late = self.GetCommData(trcode, rqname, i, '수익률(%)')
                current_price = self.GetCommData(trcode, rqname, i, '현재가')
                total_exec_price = self.GetCommData(trcode, rqname, i, '매입금액')
                possible_quantity = self.GetCommData(trcode, rqname, i, '매매가능수량')

                code = code[1:]
                self.myStock.append({'code':code, 'codeName':codeName, '보유수량':int(stock_quantity), '매입가':int(buy_price),
                                     '수익률':float(earn_late), '현재가':int(current_price), '매입금액':int(total_exec_price), '매매가능수량':int(possible_quantity)})
            if next == '2':
                self.get_myStock(next=next)
            else:
                self.stop_screen(self.screen_myInfo)
                self.block = False

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

            if next == '2':
                self.get_not_signed_stock(next=next)
            else:
                self.stop_screen(self.screen_myInfo)
                self.block = False
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
                data = {'code':code, 'date':date, 'open':int(open), 'high':int(high), 'low':int(low), 'close':int(close), 'volume':int(volume), 'trading':int(trading)}
                self.chart.append(data.copy())

            if not isLast:
                if next == '2':
                    self.chartData(type='daily', code=code, next=next)
                else:
                    self.stop_screen(self.screen_chart)
                    self.block = False
            else:
                self.block = False

        elif rqname == '주식분봉차트조회':
            code = self.GetCommData(trcode, rqname, 0, '종목코드')
            cnt = self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, rqname)

            for i in range(cnt):
                timestamp = self.GetCommData(trcode, rqname, i, '체결시간')
                open = self.GetCommData(trcode, rqname, i, '시가')
                high = self.GetCommData(trcode, rqname, i, '고가')
                low = self.GetCommData(trcode, rqname, i, '저가')
                close = self.GetCommData(trcode, rqname, i, '현재가')
                volume = self.GetCommData(trcode, rqname, i, '거래량')

                data = {'code':code, 'timestamp':timestamp, 'open':int(open), 'high':int(high), 'low':int(low), 'close':int(close), 'volume':int(volume)}
                self.chart.append(data.copy())

            self.stop_screen(self.screen_chart)
            self.block = False

        else:
            print(sScrNo, sRecordName, rqname, trcode)

    def realdata_slot(self, code, type, sRealData):

        if type == '장시작시간':
            self.logger.info('장시작시간')
            value = self.GetCommRealData(code, self.realType.REALTYPE[type]['장운영구분'])  # (0:장시작전, 2:장종료전, 3:장시작)
            fid_mean = None
            if value == '0':
                fid_mean = '장시작 전'
            elif value == '3':
                fid_mean = '장시작'
            elif value == '2':
                fid_mean = '장종료, 동시호가로 넘어감 '
            elif value == '4':
                fid_mean = '3시간30분 장 종료'
            self.logger.info('%s: %s'%(type, fid_mean))

        elif type == '주식체결':
            timestamp = self.GetCommRealData(code, self.realType.REALTYPE[type]['체결시간'])
            close = self.GetCommRealData(code, self.realType.REALTYPE[type]['현재가'])
            compared = self.GetCommRealData(code, self.realType.REALTYPE[type]['전일대비'])
            fluctuation = self.GetCommRealData(code, self.realType.REALTYPE[type]['등락율'])
            ask = self.GetCommRealData(code, self.realType.REALTYPE[type]['(최우선)매도호가'])
            bid = self.GetCommRealData(code, self.realType.REALTYPE[type]['(최우선)매수호가'])
            quantity = self.GetCommRealData(code, self.realType.REALTYPE[type]['거래량'])
            volume = self.GetCommRealData(code, self.realType.REALTYPE[type]['누적거래량'])
            high = self.GetCommRealData(code, self.realType.REALTYPE[type]['고가'])
            open = self.GetCommRealData(code, self.realType.REALTYPE[type]['시가'])
            low = self.GetCommRealData(code, self.realType.REALTYPE[type]['저가'])

            self.realStockData[code] = {'timestamp':timestamp, 'close':int(close.lstrip('+').lstrip('-')), '전일대비':int(compared), '등락률':float(fluctuation),
                         'ask':abs(int(ask)), 'bid':abs(int(bid)), '거래량':int(quantity), 'volume':abs(int(volume)),
                         'high':int(high), 'open':int(open), 'low':int(low.lstrip('+').lstrip('-'))}

    # login
    def login(self):
        self.dynamicCall('CommConnect()')   # dynamicCall은 pyQt5에서 제공하는 함수로 서버에 데이터를 송수신해 주는 역할을 함
        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()

    # account
    def get_account_list(self):
        account_list = self.dynamicCall('GetLoginInfo(QString)', 'ACCNO')
        account_list = account_list.split(';')[:-1]
        return account_list

    def get_account_info(self, account_num, next='0'):
        rqname = '예수금상세현황요청'
        self.logger.info(rqname)
        self.SetInputValue('계좌번호', account_num)
        self.SetInputValue('비밀번호', self.account_secret)
        self.SetInputValue('비밀번호입력매체구분', '00')
        self.SetInputValue('조회구분', '3')
        self.CommRqData(rqname, 'opw00001', next, self.screen_myInfo)

        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()
        return {'account':account_num, '예수금':self.deposit, '출금가능금액':self.output_deposit}

    def get_myStock(self, account_num, next='0'):
        rqname = '계좌평가잔고내역요청'
        self.logger.info(rqname)
        self.SetInputValue('계좌번호', account_num)
        self.SetInputValue('비밀번호', self.account_secret)
        self.SetInputValue('비밀번호입력매체구분', '00')
        self.SetInputValue('조회구분', '1')
        self.CommRqData(rqname, 'opw00018', next, self.screen_myInfo)

        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.profit, self.myStock

    def get_not_signed_stock(self, account_num, next='0'):
        rqname = '실시간미체결요청'
        self.logger.info(rqname)
        self.SetInputValue('계좌번호', account_num)
        self.SetInputValue('매매구분', '0') # 매매구분 = 0:전체, 1:매도, 2:매수
        self.SetInputValue('체결구분', '1') # 체결구분 = 0:전체, 2:체결, 1:미체결
        self.CommRqData(rqname, 'opt10075', next, self.screen_myInfo)

        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.not_signed_stock

    def get_code_list(self, market='0'):
        code_list = self.dynamicCall('GetCodeListByMarket(QString)', market)
        code_list = code_list.split(';')[:-1]
        return code_list

    def get_codeName(self, code):
        codeName = self.dynamicCall('GetMasterCodeName(QString)', code)
        return codeName

    # chart
    def get_chart(self, type='daily', code=None, lastDate=None):
        self.block = True
        self.chart = []
        self.lastDate = lastDate
        self.disconnectRealData()
        self.chartData(type=type, code=code)
        while self.block:
            pythoncom.PumpWaitingMessages()
        self.lastDate = None
        return self.chart

    def chartData(self, type='daily', code=None, date=None, next='0'):
        self.SetInputValue('종목코드', code)
        self.SetInputValue('수정주가부분', '1')
        if type == 'daily':
            QTest.qWait(5000)
            if date is not None:
                self.SetInputValue('기준일자', date)
            self.CommRqData('주식일봉차트조회', 'opt10081', next, self.screen_chart)
        elif type == 'min':
            self.SetInputValue('틱범위', '1')
            self.CommRqData('주식분봉차트조회', 'opt10080', next, self.screen_chart)

    # realData
    def realdata(self, code):
        self.dynamicCall('SetRealReg(QString, QString, QString, QString)',
                         self.screen_start_stop_real, code, '20', '0')

    # order
    def order(self, account_num, code, quantity, price, trade, orderType='지정가', orderNo=''):
        order = [trade, self.screen_meme, account_num, self.realType.SENDTYPE['trade'][trade],
                 code, quantity, price, self.realType.SENDTYPE['orderType'][orderType], orderNo]
        self.logger.info('SendOrder : %s' %str(order))
        order_msg = self.dynamicCall('SendOrder(QString, QString, QString, int, QSting, int, int, QString, QString)',order)
        return order_msg

    # screen
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
            real_screen = int(self.screen_real)
            meme_screen = int(self.screen_meme)
            if (cnt%50) == 0:
                real_screen = real_screen + 1
                meme_screen = meme_screen + 1
                self.screen_real = str(real_screen)
                self.screen_meme = str(meme_screen)

            if code in self.portfolio:
                self.portfolio[code]['스크린번호'] = self.screen_real
                self.portfolio[code]['주문용스크린번호'] = self.screen_meme
            else:
                self.portfolio[code]= {'스크린번호':self.screen_real, '주문용스크린번호':self.screen_meme}

            cnt = cnt + 1








