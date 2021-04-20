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
        self.accountSecret = '0000'
        self.accountInfo = {}

        # pythoncom
        self.block = True

        # realData
        self.tradeData = {}
        self.orderBook = {}

        # 요청 스크린 번호
        self.screenMyInfo = '2000' # 계좌 관련한 스크린 번호
        self.screenChart = '4000'
        self.screenReal = '5000'
        self.screenMeme = '6000'
        self.screenStartStopReal = '1000' # 장 시작/종료 실시간 스크린 번호

       # 초기 세팅 함수들
        self.getOcxInstance()  # OCX 방식을 파이썬에 사용할 수 있게 변환해 주는 함수
        self.eventSlots()  # 키움과 연결하기 위한 시그널 /슬롯 모음, login, trade, realdata, chejan

    def getOcxInstance(self):
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

    def _stopScreen(self, screen=None):
        self.dynamicCall('DisconnectRealData(QString)', screen)

    # slots
    def eventSlots(self):
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
            ordPossible = self._GetCommData(trcode, rqname, 0, '주문가능금액')

            self.deposit = int(deposit)
            self.outputDeposit = int(outputDeposit)
            self.accountInfo = {'예수금':int(deposit), '출금가능금액':int(outputDeposit), '주문가능금액':int(ordPossible)}

            self._stopScreen(self.screenMyInfo)
            self.block = False

        elif rqname == '계좌평가잔고내역':
            buyMoney = self._GetCommData(trcode, rqname, 0, '총매입금액')
            lossMoney = self._GetCommData(trcode, rqname, 0, '총평가손익금액')
            lossRate = self._GetCommData(trcode, rqname, 0, '총수익률(%)')
            if buyMoney == '':
                buyMoney = 0
            self.profit['총매입금액'] = int(buyMoney)
            self.profit['총평가손익금액'] = int(lossMoney)
            self.profit['총수익률(%)'] = float(lossRate)

            cnt = self._GetRepeatCnt(trcode, rqname)
            for i in range(cnt):
                code = self._GetCommData(trcode, rqname, i, '종목번호')
                codeName = self._GetCommData(trcode, rqname, i, '종목명')
                stockQty = self._GetCommData(trcode, rqname, i, '보유수량')
                buyPrice = self._GetCommData(trcode, rqname, i, '매입가')
                earnRate = self._GetCommData(trcode, rqname, i, '수익률(%)')
                currentPrice = self._GetCommData(trcode, rqname, i, '현재가')
                totalExecPrice = self._GetCommData(trcode, rqname, i, '매입금액')
                possibleQty = self._GetCommData(trcode, rqname, i, '매매가능수량')

                code = code[1:]
                self.myStock.append({'code':code, 'codeName':codeName, '보유수량':int(stockQty), '매입가':int(buyPrice),
                                     '수익률':float(earnRate), '현재가':int(currentPrice), '매입금액':int(totalExecPrice), '매매가능수량':int(possibleQty)})
            if next == '2':
                self.myStockData(next=next)
            else:
                self._stopScreen(self.screenMyInfo)
                self.block = False

        elif rqname == '체결확인':
            cnt = self._GetRepeatCnt(trcode, rqname)
            for i in range(cnt):
                code = self._GetCommData(trcode, rqname, i, '종목코드')
                codeName = self._GetCommData(trcode, rqname, i, '종목명')
                ordNo = self._GetCommData(trcode, rqname, i, '주문번호')
                ordStatus = self._GetCommData(trcode, rqname, i, '주문상태')
                qty = self._GetCommData(trcode, rqname, i, '주문수량')
                ordPrice = self._GetCommData(trcode, rqname, i, '주문가격')
                price = self._GetCommData(trcode, rqname, i, '체결가')
                ordType = self._GetCommData(trcode, rqname, i, '주문구분').lstrip('+').lstrip('-')
                notQty = self._GetCommData(trcode, rqname, i, '미체결수량')
                okQty = self._GetCommData(trcode, rqname, i, '체결량')
                timestamp = self._GetCommData(trcode, rqname, i, '주문시간')

                data= {'timestamp':timestamp, 'code':code, 'codeName':codeName, 'ordNo':int(ordNo), '주문상태':ordStatus, '주문수량':int(qty),
                        '주문가격':int(ordPrice), '주문구분':ordType, '미체결수량':int(notQty), '체결량':int(okQty), '체결가':price}
                self.signed[code] = data.copy()
            if next == '2':
                self.signedData(next=next)
            else:
                self._stopScreen(self.screenMyInfo)
                self.block = False

        elif rqname == '미체결확인':
            cnt = self._GetRepeatCnt(trcode, rqname)
            for i in range(cnt):
                code = self._GetCommData(trcode, rqname, i, '종목코드')
                codeName = self._GetCommData(trcode, rqname, i, '종목명')
                ordNo = self._GetCommData(trcode, rqname, i, '주문번호')
                ordStatus = self._GetCommData(trcode, rqname, i, '주문상태')
                qty = self._GetCommData(trcode, rqname, i, '주문수량')
                ordPrice = self._GetCommData(trcode, rqname, i, '주문가격')
                trade = self._GetCommData(trcode, rqname, i, '주문구분').lstrip('+').lstrip('-')
                notQty = self._GetCommData(trcode, rqname, i, '미체결수량')
                okQty = self._GetCommData(trcode, rqname, i, '체결량')
                timestamp = self._GetCommData(trcode, rqname, i, '시간')

                data = {'timestamp':timestamp, 'code':code, 'codeName':codeName, 'ordNo':int(ordNo), '주문상태':ordStatus, '주문수량':int(qty),
                                        '주문가격':int(ordPrice), '주문구분':trade, '미체결수량':int(notQty), '체결량':int(okQty)}
                self.notSigned[ordNo] = data.copy()
            if next == '2':
                self.notSignedData(next=next)
            else:
                self._stopScreen(self.screenMyInfo)
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
                    self._stopScreen(self.screenChart)
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

            self._stopScreen(self.screenChart)
            self.block = False

        # sendOrder시 예시) rqname : '신규매도'

    def _realdataSlot(self, code, sType, realData):

        if sType == '장시작시간':
            self.logger.info('장시작시간')
            value = self._GetCommRealData(code, self.realType.REALTYPE[sType]['장운영구분'])  # (0:장시작전, 2:장종료전, 3:장시작)
            fid = None
            if value == '0':
                fid = '장시작 전'
            elif value == '3':
                fid = '장시작'
            elif value == '2':
                fid = '장종료, 동시호가로 넘어감 '
            elif value == '4':
                fid = '3시간30분 장 종료'
            self.logger.info('%s: %s' % (sType, fid))

        elif sType == '주식체결':
            timestamp = self._GetCommRealData(code, self.realType.REALTYPE[sType]['체결시간'])
            close = self._GetCommRealData(code, self.realType.REALTYPE[sType]['현재가']).lstrip('+').lstrip('-')
            compared = self._GetCommRealData(code, self.realType.REALTYPE[sType]['전일대비'])
            fluctuation = self._GetCommRealData(code, self.realType.REALTYPE[sType]['등락율'])
            ask = self._GetCommRealData(code, self.realType.REALTYPE[sType]['(최우선)매도호가'])
            bid = self._GetCommRealData(code, self.realType.REALTYPE[sType]['(최우선)매수호가'])
            qty = self._GetCommRealData(code, self.realType.REALTYPE[sType]['거래량'])
            volume = self._GetCommRealData(code, self.realType.REALTYPE[sType]['누적거래량'])
            high = self._GetCommRealData(code, self.realType.REALTYPE[sType]['고가']).lstrip('+').lstrip('-')
            open = self._GetCommRealData(code, self.realType.REALTYPE[sType]['시가']).lstrip('+').lstrip('-')
            low = self._GetCommRealData(code, self.realType.REALTYPE[sType]['저가']).lstrip('+').lstrip('-')

            qty = int(qty)
            self.tradeData[code] = {'timestamp':timestamp, 'close':int(close), '전일대비':int(compared), '등락률':float(fluctuation),
                         'ask':abs(int(ask)), 'bid':abs(int(bid)), '거래량':qty, 'volume':abs(int(volume)),
                         'high':int(high), 'open':int(open), 'low':int(low)}
            if qty > 0:
                self.tradeData[code]['buyQty'] = self.tradeData[code]['buyQty'] + qty
            if qty < 0:
                self.tradeData[code]['sellQty'] = self.tradeData[code]['sellQty'] + qty

        elif sType == '주식호가잔량':
            timestamp = self._GetCommRealData(code, self.realType.REALTYPE[sType]['호가시간'])
            askPrice1 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가1']).lstrip('+').lstrip('-')
            askPrice2 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가2']).lstrip('+').lstrip('-')
            askPrice3 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가3']).lstrip('+').lstrip('-')
            askPrice4 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가4']).lstrip('+').lstrip('-')
            askPrice5 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가5']).lstrip('+').lstrip('-')
            askPrice6 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가6']).lstrip('+').lstrip('-')
            askPrice7 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가7']).lstrip('+').lstrip('-')
            askPrice8 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가8']).lstrip('+').lstrip('-')
            askPrice9 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가9']).lstrip('+').lstrip('-')
            askPrice10 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가10']).lstrip('+').lstrip('-')
            askQty1 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량1'])
            askQty2 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량2'])
            askQty3 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량3'])
            askQty4 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량4'])
            askQty5 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량5'])
            askQty6 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량6'])
            askQty7 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량7'])
            askQty8 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량8'])
            askQty9 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량9'])
            askQty10 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가수량10'])
            bidPrice1 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가1']).lstrip('+').lstrip('-')
            bidPrice2 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가2']).lstrip('+').lstrip('-')
            bidPrice3 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가3']).lstrip('+').lstrip('-')
            bidPrice4 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가4']).lstrip('+').lstrip('-')
            bidPrice5 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가5']).lstrip('+').lstrip('-')
            bidPrice6 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가6']).lstrip('+').lstrip('-')
            bidPrice7 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가7']).lstrip('+').lstrip('-')
            bidPrice8 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가8']).lstrip('+').lstrip('-')
            bidPrice9 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가9']).lstrip('+').lstrip('-')
            bidPrice10 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가10']).lstrip('+').lstrip('-')
            bidQty1 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량1'])
            bidQty2 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량2'])
            bidQty3 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량3'])
            bidQty4 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량4'])
            bidQty5 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량5'])
            bidQty6 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량6'])
            bidQty7 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량7'])
            bidQty8 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량8'])
            bidQty9 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량9'])
            bidQty10 = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가수량10'])
            askTotalQty = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도호가총잔량'])
            bidTotalQty = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수호가총잔량'])
            bidReg = self._GetCommRealData(code, self.realType.REALTYPE[sType]['순매수잔량'])
            askReg = self._GetCommRealData(code, self.realType.REALTYPE[sType]['순매도잔량'])
            bidRatio = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매수비율'])
            askRatio = self._GetCommRealData(code, self.realType.REALTYPE[sType]['매도비율'])

            asks = [[int(askPrice1), int(askQty1)], [int(askPrice2), int(askQty2)], [int(askPrice3), int(askQty3)], [int(askPrice4), int(askQty4)], [int(askPrice5), int(askQty5)],
                   [int(askPrice6), int(askQty6)], [int(askPrice7), int(askQty7)], [int(askPrice8), int(askQty8)], [int(askPrice9), int(askQty9)], [int(askPrice10), int(askQty10)]]
            bids = [[int(bidPrice1), int(bidQty1)], [int(bidPrice2), int(bidQty2)], [int(bidPrice3), int(bidQty3)], [int(bidPrice4), int(bidQty4)], [int(bidPrice5), int(bidQty5)],
                   [int(bidPrice6), int(bidQty6)], [int(bidPrice7), int(bidQty7)], [int(bidPrice8), int(bidQty8)], [int(bidPrice9), int(bidQty9)], [int(bidPrice10), int(bidQty10)]]
            self.orderBook[code] = {'timestamp':timestamp, 'asks':asks, 'bids':bids, 'askTotalQty':int(askTotalQty), 'bidTotalQty':int(bidTotalQty),
                                    'bidReg':int(bidReg), 'askReg':int(askReg), 'bidRatio':float(bidRatio), 'askRatio':float(askRatio) }

    def _chejanSlot(self, gubun, itemCnt, fidList):
        if int(gubun) == 0:
            accountNum = self._GetChejanData(self.realType.REALTYPE['주문체결']['계좌번호'])
            timestamp = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문/체결시간'])
            ordNo = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문번호'])
            code = self._GetChejanData(self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            codeName = self._GetChejanData(self.realType.REALTYPE['주문체결']['종목명']).strip()
            originOrdNo = self._GetChejanData(self.realType.REALTYPE['주문체결']['원주문번호'])
            qty = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문수량'])
            ordPrice = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문가격'])
            price = self._GetChejanData(self.realType.REALTYPE['주문체결']['체결가'])
            trade = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문구분']).lstrip('+').lstrip('-')
            okQty = self._GetChejanData(self.realType.REALTYPE['주문체결']['체결량'])
            notQty = self._GetChejanData(self.realType.REALTYPE['주문체결']['미체결수량'])
            ordStatus = self._GetChejanData(self.realType.REALTYPE['주문체결']['주문상태'])

            if price == '':
                price = 0
            if okQty == '':
                okQty = 0
            data = {'timestamp':timestamp, 'code':code, 'codeName':codeName, 'ordNo':int(ordNo),
                    '주문상태':ordStatus, '주문수량':int(qty), 'price':int(price),
                    '주문가격':int(ordPrice), '주문구분':trade, '미체결수량':int(notQty),
                    '체결량':int(okQty)}
            self.notSigned[ordNo] = data.copy()

        elif int(gubun) == 1:
            code = self._GetChejanData(self.realType.REALTYPE['잔고']['종목코드'])[1:]
            codeName = self._GetChejanData(self.realType.REALTYPE['잔고']['종목명']).strip()
            currentPrice = self._GetChejanData(self.realType.REALTYPE['잔고']['현재가'])
            stockQty = self._GetChejanData(self.realType.REALTYPE['잔고']['보유수량'])
            buyPrice = self._GetChejanData(self.realType.REALTYPE['잔고']['총매입가'])
            totalExecPrice = self._GetChejanData(self.realType.REALTYPE['잔고']['매입단가'])
            possibleQty = self._GetChejanData(self.realType.REALTYPE['잔고']['주문가능수량'])
            data = {'code':code, 'codeName': codeName, '보유수량': int(stockQty), '매입가':int(buyPrice),
                                 '현재가':int(currentPrice), '매입금액': int(totalExecPrice),
                                 '매매가능수량':int(possibleQty)}
            self.signed[code] = data.copy()
            if int(stockQty) == 0:
                del self.signed[code]

    # login
    def login(self):
        self.dynamicCall('CommConnect()')   # dynamicCall은 pyQt5에서 제공하는 함수로 서버에 데이터를 송수신해 주는 역할을 함
        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()

    # account
    def getAccountList(self):
        accountList = self.dynamicCall('GetLoginInfo(QString)', 'ACCNO')
        accountList = accountList.split(';')[:-1]
        return accountList

    def getAccountInfo(self, accountNum, next='0'):
        rqname = '예수금상세현황'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', accountNum)
        self._SetInputValue('비밀번호', self.accountSecret)
        self._SetInputValue('비밀번호입력매체구분', '00')
        self._SetInputValue('조회구분', '3')
        self._CommRqData(rqname, 'opw00001', next, self.screenMyInfo)

        self.block = True
        while self.block:
            pythoncom.PumpWaitingMessages()
        self.accountInfo['account'] = accountNum
        return self.accountInfo

    def getMyStock(self, accountNum):
        self.myStock = []
        self.block = True
        self.myStockData(accountNum)
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.profit, self.myStock

    def myStockData(self, accountNum, next='0'):
        rqname = '계좌평가잔고내역'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', accountNum)
        self._SetInputValue('비밀번호', self.accountSecret)
        self._SetInputValue('비밀번호입력매체구분', '00')
        self._SetInputValue('조회구분', '1')
        self._CommRqData(rqname, 'opw00018', next, self.screenMyInfo)

    def getSigned(self, accountNum):
        self.signed = {}
        self.block = True
        self.signedData(accountNum)
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.signed

    def signedData(self, accountNum, next='0'):
        rqname = '체결확인'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', accountNum)
        self._SetInputValue('매매구분', '0')  # 매매구분 = 0:전체, 1:매도, 2:매수
        self._SetInputValue('체결구분', '2')  # 체결구분 = 0:전체, 2:체결, 1:미체결
        self._CommRqData(rqname, 'opt10076', next, self.screenMyInfo)

    def getNotSigned(self, accountNum):
        self.notSigned = {}
        self.block = True
        self.notSignedData(accountNum)
        while self.block:
            pythoncom.PumpWaitingMessages()
        return self.notSigned

    def notSignedData(self, accountNum, next='0'):
        rqname = '미체결확인'
        self.logger.info(rqname)
        self._SetInputValue('계좌번호', accountNum)
        self._SetInputValue('매매구분', '0')  # 매매구분 = 0:전체, 1:매도, 2:매수
        self._SetInputValue('체결구분', '1')  # 체결구분 = 0:전체, 2:체결, 1:미체결
        self._CommRqData(rqname, 'opt10075', next, self.screenMyInfo)

    def getCodeList(self, market='0'):
        codeList = self.dynamicCall('GetCodeListByMarket(QString)', market)
        codeList = codeList.split(';')[:-1]
        return codeList

    def getCodeName(self, code):
        codeName = self.dynamicCall('GetMasterCodeName(QString)', code)
        return codeName

    # chart
    def getChart(self, type='daily', code=None, lastDate=None):
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
            self._CommRqData('일봉차트', 'opt10081', next, self.screenChart)
        elif type == 'min':
            self._SetInputValue('틱범위', '1')
            self._CommRqData('분봉차트', 'opt10080', next, self.screenChart)

    # realData
    def realdata(self, code):
        # 손가락 하나 까딱하지 않는 주식 거래 시스템 구축 p222
        # RealType에 포함된 유일한 FID 번호 하나만 입력해도 관련된 RealType의 모든 데이터를 슬롯에 보내준다.
        # '20' 체결시간 - 주식체결, '41 매도호가1https://download.kiwoom.com/hero4_help_new/0196.htm - 주식호가잔량
        # https://wikidocs.net/92604
        self.dynamicCall('SetRealReg(QString, QString, QString, QString)',
                         self.screenStartStopReal, code, '20;41', '0')

    # order
    def sendOrder(self, accountNum, code, qty, price, trade, ordType='지정가', ordNo=''):
        order = [trade, self.screenMeme, accountNum, self.realType.SENDTYPE['trade'][trade],
                 code, qty, price, self.realType.SENDTYPE['orderType'][ordType], ordNo]
        self.logger.info('SendOrder: %s' %str(order))
        ordMsg = self.dynamicCall('SendOrder(QString, QString, QString, int, QSting, int, int, QString, QString)', order)
        return ordMsg

    # screen
    def screenNumberSetting(self):
        screenOverwrite = []

        # 계좌평가잔고내역에 있는 종목들
        for code in self.myStock:
            if code not in screenOverwrite:
                screenOverwrite.append(code)

        # 미체결에 있는 종목들
        for ordNo in self.notSigned:
            code = self.notSigned[ordNo]['종목코드']

            if code not in screenOverwrite:
                screenOverwrite.append(code)

        # 포트폴리오에 있는 종목들
        for code in self.portfolio:
            if code not in screenOverwrite:
                screenOverwrite.append(code)

        # 스크린 번호 할당
        cnt = 0
        for code in screenOverwrite:
            realScreen = int(self.screenReal)
            memeScreen = int(self.screenMeme)
            if (cnt%50) == 0:
                realScreen = realScreen + 1
                memeScreen = memeScreen + 1
                self.screenReal = str(realScreen)
                self.screenMeme = str(memeScreen)

            if code in self.portfolio:
                self.portfolio[code]['스크린번호'] = self.screenReal
                self.portfolio[code]['주문용스크린번호'] = self.screenMeme
            else:
                self.portfolio[code]= {'스크린번호':self.screenReal, '주문용스크린번호':self.screenMeme}

            cnt = cnt + 1








