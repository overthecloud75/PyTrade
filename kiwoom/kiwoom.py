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
        self.signed = {}
        self.notSigned = {}
        self.account_secret = '0000'
        self.accountInfo = {}

        # pythoncom
        self.block = True

        # realData
        self.realStockData = {}
        self.orderbook = {}

        # 요청 스크린 번호
        self.screen_myInfo = '2000' # 계좌 관련한 스크린 번호
        self.screen_chart = '4000'
        self.screen_real = '5000'
        self.screen_meme = '6000'
        self.screen_start_stop_real = '1000' # 장 시작/종료 실시간 스크린 번호

       # 초기 세팅 함수들
        self.get_ocx_instance()  # OCX 방식을 파이썬에 사용할 수 있게 변환해 주는 함수
        self.event_slots()  # 키움과 연결하기 위한 시그널 /슬롯 모음, login, trade, realdata, chejan

    def get_ocx_instance(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')  # ocx 확장자도 파이썬에서 사용할 수 있게 해 준다.
                                                      # registery에 저장된 API 모듈 불러오기

    # dynamicCall
    def _SetInputValue(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def _CommRqData(self, rqname, trcode, next, screen):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen)

    def _GetCommData(self, trcode, rqname, index, item):
        data = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, index, item)
        return data.strip()

    def _GetCommRealData(self, code, fid):
        data = self.dynamicCall("GetCommRealData(QString, int)", code, fid)
        return data

    def _GetRepeatCnt(self, trcode, rqname):
        cnt = self.dynamicCall('GetRepeatCnt(Qstring, Qstring)', trcode, rqname)
        return cnt

    def _GetChejanData(self, fid):
        data = self.dynamicCall('GetChejanData(int)', fid)
        return data

    def _stop_screen(self, screen=None):
        self.dynamicCall('DisconnectRealData(QString)', screen)

    # slots
    def event_slots(self):
        self.OnEventConnect.connect(self._loginSlot)
        self.OnReceiveTrData.connect(self._tradataSlot)
        self.OnReceiveRealData.connect(self._realdataSlot)
        self.OnReceiveChejanData.connect(self._chejanSlot)

    def _loginSlot(self, errCode):
        self.logger.info('login status: %s' %errors(errCode))
        self.lastErrCode = errCode
        self.block = False

    def _tradataSlot(self, screen, rqname, trcode, record, next):
        if rqname == '예수금상세현황':
            deposit = self._GetCommData(trcode, rqname, 0, '예수금')
            outputDeposit = self._GetCommData(trcode, rqname, 0, '출금가능금액')
            orderPossible = self._GetCommData(trcode, rqname, 0, '주문가능금액')

            self.deposit = int(deposit)
            self.output_deposit = int(outputDeposit)
            self.accountInfo = {'예수금':int(deposit), '출금가능금액':int(outputDeposit), '주문가능금액':int(orderPossible)}

            self._stop_screen(self.screen_myInfo)
            self.block = False

        elif rqname == '계좌평가잔고내역':
            buy_money = self._GetCommData(trcode, rqname, 0, '총매입금액')
            loss_money = self._GetCommData(trcode, rqname, 0, '총평가손익금액')
            loss_rate = self._GetCommData(trcode, rqname, 0, '총수익률(%)')
            if buy_money == '':
                buy_money = 0
            self.profit['총매입금액'] = int(buy_money)
            self.profit['총평가손익금액'] = int(loss_money)
            self.profit['총수익률(%)'] = float(loss_rate)

            cnt = self._GetRepeatCnt(trcode, rqname)
            for i in range(cnt):
                code = self._GetCommData(trcode, rqname, i, '종목번호')
                codeName = self._GetCommData(trcode, rqname, i, '종목명')
                stock_quantity = self._GetCommData(trcode, rqname, i, '보유수량')
                buy_price = self._GetCommData(trcode, rqname, i, '매입가')
                earn_late = self._GetCommData(trcode, rqname, i, '수익률(%)')
                current_price = self._GetCommData(trcode, rqname, i, '현재가')
                total_exec_price = self._GetCommData(trcode, rqname, i, '매입금액')
                possible_quantity = self._GetCommData(trcode, rqname, i, '매매가능수량')

                code = code[1:]
                self.myStock.append({'code':code, 'codeName':codeName, '보유수량':int(stock_quantity), '매입가':int(buy_price),
                                     '수익률':float(earn_late), '현재가':int(current_price), '매입금액':int(total_exec_price), '매매가능수량':int(possible_quantity)})
            if next == '2':
                self.myStockData(next=next)
            else:
                self._stop_screen(self.screen_myInfo)
                self.block = False

        elif rqname == '체결확인':
            cnt = self._GetRepeatCnt(trcode, rqname)
            for i in range(cnt):
                code = self._GetCommData(trcode, rqname, i, '종목코드')
                codeName = self._GetCommData(trcode, rqname, i, '종목명')
                orderNo = self._GetCommData(trcode, rqname, i, '주문번호')
                orderStatus = self._GetCommData(trcode, rqname, i, '주문상태')
                quantity = self._GetCommData(trcode, rqname, i, '주문수량')
                order_price = self._GetCommData(trcode, rqname, i, '주문가격')
                price = self._GetCommData(trcode, rqname, i, '체결가')
                order_type = self._GetCommData(trcode, rqname, i, '주문구분')
                not_quantity = self._GetCommData(trcode, rqname, i, '미체결수량')
                ok_quantity = self._GetCommData(trcode, rqname, i, '체결량')
                timestamp = self._GetCommData(trcode, rqname, i, '주문시간')

                data= {'timestamp':timestamp, 'code':code, 'codeName':codeName, 'orderNo':int(orderNo), '주문상태':orderStatus, '주문수량':int(quantity),
                        '주문가격':int(order_price), '주문구분':order_type.lstrip('+').lstrip('-'), '미체결수량':int(not_quantity), '체결량':int(ok_quantity), '체결가':price}
                self.signed[code] = data.copy()
            if next == '2':
                self.signedData(next=next)
            else:
                self._stop_screen(self.screen_myInfo)
                self.block = False

        elif rqname == '미체결확인':
            cnt = self._GetRepeatCnt(trcode, rqname)
            for i in range(cnt):
                code = self._GetCommData(trcode, rqname, i, '종목코드')
                codeName = self._GetCommData(trcode, rqname, i, '종목명')
                orderNo = self._GetCommData(trcode, rqname, i, '주문번호')
                orderStatus = self._GetCommData(trcode, rqname, i, '주문상태')
                quantity = self._GetCommData(trcode, rqname, i, '주문수량')
                order_price = self._GetCommData(trcode, rqname, i, '주문가격')
                trade = self._GetCommData(trcode, rqname, i, '주문구분')
                not_quantity = self._GetCommData(trcode, rqname, i, '미체결수량')
                ok_quantity = self._GetCommData(trcode, rqname, i, '체결량')
                timestamp = self._GetCommData(trcode, rqname, i, '시간')

                data = {'timestamp':timestamp, 'code':code, 'codeName':codeName, 'orderNo':int(orderNo), '주문상태':orderStatus, '주문수량':int(quantity),
                                        '주문가격':int(order_price), '주문구분':trade.lstrip('+').lstrip('-'), '미체결수량':int(not_quantity), '체결량':int(ok_quantity)}
                self.notSigned[orderNo] = data.copy()
            if next == '2':
                self.notSignedData(next=next)
            else:
                self._stop_screen(self.screen_myInfo)
                self.block = False

        elif rqname == '일봉차트':
            isLast = False
            code = self._GetCommData(trcode, rqname, 0, '종목코드')
            cnt = self._GetRepeatCnt(trcode, rqname)

            for i in range(cnt):
                date = self._GetCommData(trcode, rqname, i, '일자')
                open = self._GetCommData(trcode, rqname, i, '시가')
                high = self._GetCommData(trcode, rqname, i, '고가')
                low = self._GetCommData(trcode, rqname, i, '저가')
                close = self._GetCommData(trcode, rqname, i, '현재가')
                volume = self._GetCommData(trcode, rqname, i, '거래량')
                trading = self._GetCommData(trcode, rqname, i, '거래대금')
                if date == self.lastDate:
                    isLast = True
                    break
                data = {'code':code, 'date':date, 'open':int(open), 'high':int(high), 'low':int(low), 'close':int(close), 'volume':int(volume), 'trading':int(trading)}
                self.chart.append(data.copy())

            if not isLast:
                if next == '2':
                    self.chartData(type='daily', code=code, next=next)
                else:
                    self._stop_screen(self.screen_chart)
                    self.block = False
            else:
                self.block = False

        elif rqname == '분봉차트':
            code = self._GetCommData(trcode, rqname, 0, '종목코드')
            cnt = self._GetRepeatCnt(trcode, rqname)

            for i in range(cnt):
                timestamp = self._GetCommData(trcode, rqname, i, '체결시간')
                open = self._GetCommData(trcode, rqname, i, '시가')
                high = self._GetCommData(trcode, rqname, i, '고가')
                low = self._GetCommData(trcode, rqname, i, '저가')
                close = self._GetCommData(trcode, rqname, i, '현재가')
                volume = self._GetCommData(trcode, rqname, i, '거래량')

                data = {'timestamp':timestamp, 'code':code, 'open':int(open), 'high':int(high), 'low':int(low), 'close':int(close), 'volume':int(volume)}
                self.chart.append(data.copy())

            self._stop_screen(self.screen_chart)
            self.block = False

        # sendOrder시 예시) rqname : '신규매도'

    def _realdataSlot(self, code, type, sRealData):

        if type == '장시작시간':
            self.logger.info('장시작시간')
            value = self._GetCommRealData(code, self.realType.REALTYPE[type]['장운영구분'])  # (0:장시작전, 2:장종료전, 3:장시작)
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
            timestamp = self._GetCommRealData(code, self.realType.REALTYPE[type]['체결시간'])
            close = self._GetCommRealData(code, self.realType.REALTYPE[type]['현재가'])
            compared = self._GetCommRealData(code, self.realType.REALTYPE[type]['전일대비'])
            fluctuation = self._GetCommRealData(code, self.realType.REALTYPE[type]['등락율'])
            ask = self._GetCommRealData(code, self.realType.REALTYPE[type]['(최우선)매도호가'])
            bid = self._GetCommRealData(code, self.realType.REALTYPE[type]['(최우선)매수호가'])
            quantity = self._GetCommRealData(code, self.realType.REALTYPE[type]['거래량'])
            volume = self._GetCommRealData(code, self.realType.REALTYPE[type]['누적거래량'])
            high = self._GetCommRealData(code, self.realType.REALTYPE[type]['고가'])
            open = self._GetCommRealData(code, self.realType.REALTYPE[type]['시가'])
            low = self._GetCommRealData(code, self.realType.REALTYPE[type]['저가'])

            self.realStockData[code] = {'timestamp':timestamp, 'close':int(close.lstrip('+').lstrip('-')), '전일대비':int(compared), '등락률':float(fluctuation),
                         'ask':abs(int(ask)), 'bid':abs(int(bid)), '거래량':int(quantity), 'volume':abs(int(volume)),
                         'high':int(high), 'open':int(open), 'low':int(low.lstrip('+').lstrip('-'))}

        elif type == '주식호가잔량':
            timestamp = self._GetCommRealData(code, self.realType.REALTYPE[type]['호가시간'])
            askPrice1 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가1'])
            askPrice2 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가2'])
            askPrice3 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가3'])
            askPrice4 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가4'])
            askPrice5 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가5'])
            askPrice6 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가6'])
            askPrice7 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가7'])
            askPrice8 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가8'])
            askPrice9 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가9'])
            askPrice10 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가10'])
            askQty1 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량1'])
            askQty2 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량2'])
            askQty3 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량3'])
            askQty4 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량4'])
            askQty5 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량5'])
            askQty6 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량6'])
            askQty7 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량7'])
            askQty8 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량8'])
            askQty9 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량9'])
            askQty10 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가수량10'])
            bidPrice1 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가1'])
            bidPrice2 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가2'])
            bidPrice3 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가3'])
            bidPrice4 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가4'])
            bidPrice5 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가5'])
            bidPrice6 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가6'])
            bidPrice7 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가7'])
            bidPrice8 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가8'])
            bidPrice9 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가9'])
            bidPrice10 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가10'])
            bidQty1 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량1'])
            bidQty2 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량2'])
            bidQty3 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량3'])
            bidQty4 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량4'])
            bidQty5 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량5'])
            bidQty6 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량6'])
            bidQty7 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량7'])
            bidQty8 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량8'])
            bidQty9 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량9'])
            bidQty10 = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가수량10'])
            askTotalQty = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도호가총잔량'])
            bidTotalQty = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수호가총잔량'])
            bidReg = self._GetCommRealData(code, self.realType.REALTYPE[type]['순매수잔량'])
            askReg = self._GetCommRealData(code, self.realType.REALTYPE[type]['순매도잔량'])
            bidRatio = self._GetCommRealData(code, self.realType.REALTYPE[type]['매수비율'])
            askRatio = self._GetCommRealData(code, self.realType.REALTYPE[type]['매도비율'])

            asks = [[int(askPrice1), int(askQty1)], [int(askPrice2), int(askQty2)], [int(askPrice3), int(askQty3)], [int(askPrice4), int(askQty4)], [int(askPrice5), int(askQty5)],
                   [int(askPrice6), int(askQty6)], [int(askPrice7), int(askQty7)], [int(askPrice8), int(askQty8)], [int(askPrice9), int(askQty9)], [int(askPrice10), int(askQty10)]]
            bids = [[int(bidPrice1), int(bidQty1)], [int(bidPrice2), int(bidQty2)], [int(bidPrice3), int(bidQty3)], [int(bidPrice4), int(bidQty4)], [int(bidPrice5), int(bidQty5)],
                   [int(bidPrice6), int(bidQty6)], [int(bidPrice7), int(bidQty7)], [int(bidPrice8), int(bidQty8)], [int(bidPrice9), int(bidQty9)], [int(bidPrice10), int(bidQty10)]]
            self.orderBook[code] = {'asks':asks, 'bids':bids, 'askTotalQty':int(askTotalQty), 'bidTotalQty':int(bidTotalQty),
                                    'bidReg':int(bidReg), 'askReg':int(askReg), 'bidRatio':float(bidRatio), 'askRatio':float(askRatio) }

    def _chejanSlot(self, gubun, item_cnt, fidList):
        if int(gubun) == 0:
            account_no = self._GetChejanData(self.realType.REALTYPE['주문체결']['계좌번호'])
            timestamp = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문/체결시간'])
            orderNo = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문번호'])
            code = self._GetChejanData(self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            codeName = self._GetChejanData(self.realType.REALTYPE['주문체결']['종목명']).strip()
            origin_orderNo = self._GetChejanData(self.realType.REALTYPE['주문체결']['원주문번호'])
            quantity = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문수량'])
            order_price = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문가격'])
            price = self._GetChejanData(self.realType.REALTYPE['주문체결']['체결가'])
            trade = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문구분'])
            ok_quantity = self._GetChejanData(self.realType.REALTYPE['주문체결']['체결량'])
            not_quantity = self._GetChejanData(self.realType.REALTYPE['주문체결']['미체결수량'])
            orderStatus = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문상태'])

            if price == '':
                price = 0
            if ok_quantity == '':
                ok_quantity = 0
            data = {'timestamp':timestamp, 'code':code, 'codeName':codeName, 'orderNo':int(orderNo),
                    '주문상태':orderStatus, '주문수량':int(quantity), 'price':int(price),
                    '주문가격':int(order_price), '주문구분':trade.lstrip('+').lstrip('-'), '미체결수량':int(not_quantity),
                    '체결량':int(ok_quantity)}
            print(gubun, data)
            self.notSigned[orderNo] = data.copy()

        elif int(gubun) == 1:
            code = self._GetChejanData(self.realType.REALTYPE['잔고']['종목코드'])[1:]
            codeName = self._GetChejanData(self.realType.REALTYPE['잔고']['종목명']).strip()
            current_price = self._GetChejanData(self.realType.REALTYPE['잔고']['현재가'])
            stock_quantity = self._GetChejanData(self.realType.REALTYPE['잔고']['보유수량'])
            buy_price = self._GetChejanData(self.realType.REALTYPE['잔고']['총매입가'])
            total_exec_price = self._GetChejanData(self.realType.REALTYPE['잔고']['매입단가'])
            possible_quantity = self._GetChejanData(self.realType.REALTYPE['잔고']['주문가능수량'])
            data = {'code':code, 'codeName': codeName, '보유수량': int(stock_quantity), '매입가':int(buy_price),
                                 '현재가':int(current_price), '매입금액': int(total_exec_price),
                                 '매매가능수량':int(possible_quantity)}
            self.signed[code] = data.copy()
            if int(stock_quantity) == 0:
                del self.signed[code]
            print(gubun, data)

    # login
    def login(self):
        self.dynamicCall('CommConnect()')   # dynamicCall은 pyQt5에서 제공하는 함수로 서버에 데이터를 송수신해 주는 역할을 함
        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()

    # account
    def get_accountList(self):
        accountList = self.dynamicCall('GetLoginInfo(QString)', 'ACCNO')
        accountList = accountList.split(';')[:-1]
        return accountList

    def get_accountInfo(self, account_num, next='0'):
        rqname = '예수금상세현황'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', account_num)
        self._SetInputValue('비밀번호', self.account_secret)
        self._SetInputValue('비밀번호입력매체구분', '00')
        self._SetInputValue('조회구분', '3')
        self._CommRqData(rqname, 'opw00001', next, self.screen_myInfo)

        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()
        self.accountInfo['account'] = account_num
        return self.accountInfo

    def get_myStock(self, account_num):
        self.myStock = []
        self.block = True
        self.myStockData(account_num)
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.profit, self.myStock

    def myStockData(self, account_num, next='0'):
        rqname = '계좌평가잔고내역'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', account_num)
        self._SetInputValue('비밀번호', self.account_secret)
        self._SetInputValue('비밀번호입력매체구분', '00')
        self._SetInputValue('조회구분', '1')
        self._CommRqData(rqname, 'opw00018', next, self.screen_myInfo)

    def get_signed(self, account_num):
        self.signed = {}
        self.block = True
        self.signedData(account_num)
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.signed

    def signedData(self, account_num, next='0'):
        rqname = '체결확인'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', account_num)
        self._SetInputValue('매매구분', '0')  # 매매구분 = 0:전체, 1:매도, 2:매수
        self._SetInputValue('체결구분', '2')  # 체결구분 = 0:전체, 2:체결, 1:미체결
        self._CommRqData(rqname, 'opt10076', next, self.screen_myInfo)

    def get_notSigned(self, account_num):
        self.notSigned = {}
        self.block = True
        self.notSignedData(account_num)
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.notSigned

    def notSignedData(self, account_num, next='0'):
        rqname = '미체결확인'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', account_num)
        self._SetInputValue('매매구분', '0')  # 매매구분 = 0:전체, 1:매도, 2:매수
        self._SetInputValue('체결구분', '1')  # 체결구분 = 0:전체, 2:체결, 1:미체결
        self._CommRqData(rqname, 'opt10075', next, self.screen_myInfo)

    def get_codeList(self, market='0'):
        codeList = self.dynamicCall('GetCodeListByMarket(QString)', market)
        codeList = codeList.split(';')[:-1]
        return codeList

    def get_codeName(self, code):
        codeName = self.dynamicCall('GetMasterCodeName(QString)', code)
        return codeName

    # chart
    def get_chart(self, type='daily', code=None, lastDate=None):
        self.block = True
        self.chart = []
        self.lastDate = lastDate
        self.chartData(type=type, code=code)
        while self.block:
            pythoncom.PumpWaitingMessages()
        self.lastDate = None
        return self.chart

    def chartData(self, type='daily', code=None, date=None, next='0'):
        self._SetInputValue('종목코드', code)
        self._SetInputValue('수정주가부분', '1')
        if type == 'daily':
            QTest.qWait(5000)
            if date is not None:
                self._SetInputValue('기준일자', date)
            self._CommRqData('일봉차트', 'opt10081', next, self.screen_chart)
        elif type == 'min':
            self._SetInputValue('틱범위', '1')
            self._CommRqData('분봉차트', 'opt10080', next, self.screen_chart)

    # realData
    def realdata(self, code):
        # 손가락 하나 까딱하지 않는 주식 거래 시스템 구축 p222
        # RealType에 포함된 유일한 FID 번호 하나만 입력해도 관련된 RealType의 모든 데이터를 슬롯에 보내준다.
        # '20' 체결시간 - 주식체결, '21 호가시간 - 주식호가잔량
        self.dynamicCall('SetRealReg(QString, QString, QString, QString)',
                         self.screen_start_stop_real, code, '20;21', '0')

    # order
    def sendOrder(self, account_num, code, quantity, price, trade, orderType='지정가', orderNo=''):
        order = [trade, self.screen_meme, account_num, self.realType.SENDTYPE['trade'][trade],
                 code, quantity, price, self.realType.SENDTYPE['orderType'][orderType], orderNo]
        self.logger.info('SendOrder: %s' %str(order))
        orderMsg = self.dynamicCall('SendOrder(QString, QString, QString, int, QSting, int, int, QString, QString)', order)
        return orderMsg

    # screen
    def screen_number_setting(self):
        screen_overwrite = []

        # 계좌평가잔고내역에 있는 종목들
        for code in self.myStock:
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for orderNo in self.notSigned:
            code = self.notSigned[orderNo]['종목코드']

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








