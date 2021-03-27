import os

from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtTest import QTest
from config.errorCode import *
from config.kiwoomType import *
import logging

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info('Kiwoom class start')

        self.realType = RealType()

        # event loop를 실행하기 위한 변수 모음
        self.login_event_loop = QEventLoop()
        self.detail_account_info_event_loop = QEventLoop()
        self.calculator_event_loop = QEventLoop()

        # 기본 정보들
        self.market_code = {'코스닥': '10'}

        # 계좌 관련된 변수
        self.account_stock_dict = {}
        self.not_account_stock_dict = {}
        self.account_num = None  # 계좌번호
        self.account_secret = '0000'
        self.deposit = 0  # 예수금
        self.use_money = 0  # 실제 투자에 사용할 금액
        self.use_money_percent = 0.5 # 예수금에서 실제 사용할 비율
        self.output_deposit = 0
        self.total_profit_loss_money = 0
        self.total_profit_loss_rate = 0

        # 종목 분석 용
        self.calcul_data = []

        # condition 맞는 종목
        self.condition_stock_path = 'files/condition_stock.txt'
        self.portfolio_stock_dict = {}

        # dict 통합
        self.stock_dict = {'계좌평가잔고내역':self.account_stock_dict,
                           '미체결종목':self.not_account_stock_dict,
                           '포토폴리오종목':self.portfolio_stock_dict}

        # 요청 스크린 번호
        self.screen_my_info = '2000' # 계좌 관련한 스크린 번호
        self.screen_calculation_stock = '4000'
        self.screen_real_stock = '5000'
        self.screen_meme_stock = '6000'
        self.screen_start_stop_real = '1000' # 장 시작/종료 실시간 스크린 번호

        # 초기 세팅 함수들
        self.get_ocx_instance()  # OCX 방식을 파이썬에 사용할 수 있게 변환해 주는 함수
        self.event_slots()       # 키움과 연결하기 위한 시그널 /슬롯 모음
        self.signal_login_commConnect()   # 로그인 요청 함수
        self.get_account_info()  # account No 확인
        self.detail_account_info()  # 예수금 상세현황 요청
        self.detail_account_mystock()  # 계좌평가잔고내역 요청
        QTimer.singleShot(5000, self.not_concluded_account)  # 실시간 미체결 요청 5000msec 후 self.not_concluded_account 실행
        #self.calculator_fnc()

        #QTest.qWait(10000)
        #self.read_code()
        self.screen_number_setting()

        QTest.qWait(5000)

        # 실시간 수신 관련 함수
        #self.logger.info('%s' % type(self.realType.REALTYPE['장시작시간']['장운영구분']))
        self.dynamicCall('SetRealReg(QString, QString, QString, QString)',
                         self.screen_start_stop_real, '005930', '20', '0') # str(self.realType.REALTYPE['장시작시간']['장운영구분']), '0')
        # '' 자리는 종목 코드가 들어가야 하나 빈 값으로 작성하면 종목이 아니라 주식 장의 시간 상태를 실시간으로 체크크

    def get_ocx_instance(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')  # ocx 확장자도 파이썬에서 사용할 수 있게 해 준다.
                                                      # registery에 저장된 API 모듈 불러오기
    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.tradata_slot)
        self.OnReceiveRealData.connect(self.realdata_slot)

    def signal_login_commConnect(self):
        self.dynamicCall('CommConnect()')   # dynamicCall은 pyQt5에서 제공하는 함수로 서버에 데이터를 송수신해 주는 역할을 함
        self.login_event_loop.exec_()       # 로그인 요청이 완료될 떄 까지 다음코드가 실행되지 않음

    def login_slot(self, err_code):
        self.logger.info(errors(err_code))
        self.login_event_loop.exit()  # 로그인 처리가 완료되면 이벤트 루프를 종료한다.

    def tradata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        self.logger.info('tradata_slot %s' %sRQName)
        if sRQName == '예수금상세현황요청':
            deposit = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, 0, '예수금')
            self.deposit = int(deposit)
            self.use_money = float(self.deposit) * self.use_money_percent / 4

            output_deposit = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, 0, '출금가능금액')
            self.output_deposit = int(output_deposit)

            self.logger.info('예수금: %s, 출금가능금액: %s' %(self.deposit, self.output_deposit))
            self.stop_screen_cancel(self.screen_my_info)
            self.detail_account_info_event_loop.exit()

        elif sRQName == '계좌평가잔고내역요청':
            total_buy_money = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, 0, '총매입금액')
            self.total_buy_money = int(total_buy_money)
            total_profit_loss_money = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, 0, '총평가손익금액')
            self.total_profit_loss_money = int(total_profit_loss_money)
            total_profit_loss_rate = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, 0, '총수익률(%)')
            self.total_profit_loss_rate = float(total_profit_loss_rate)

            self.logger.info('총매입금액: %s, 출금가능금액: %s, 총 수익률: %s' % (str(self.total_buy_money), str(self.total_profit_loss_money), str(self.total_profit_loss_rate)))

            rows = self.dynamicCall('GetRepeatCnt(Qstring, Qstring)', sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '종목번호')
                self.logger.info('code: %s' %code)
                code_nm = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '종목명')
                stock_quantity = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '보유수량')
                buy_price = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '매입가')
                earn_late = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '수익률(%)')
                current_price = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '현재가')
                total_exec_price = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '매입금액')
                possible_quantity = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '매매가능수량')

                code = code.strip()[1:]
                if code in self.account_stock_list:
                    pass
                else:
                    self.account_stock_list[code] = {}

                self.account_stock_dict[code]['종목명'] = code_nm.strip()
                self.account_stock_dict[code]['보유수량'] =  int(stock_quantity.strip())
                self.account_stock_dict[code]['매입가'] = int(buy_price.strip())
                self.account_stock_dict[code]['수익률'] = float(earn_late.strip())
                self.account_stock_dict[code]['현재가'] = int(current_price.strip())
                self.account_stock_dict[code]['매입금액'] = int(total_exec_price.strip())
                self.account_stock_dict[code]['매매가능수량'] = int(possible_quantity.strip())

            if sPrevNext == '2':
                self.detail_account_mystock(sPrevNext='2')
            else:
                self.stop_screen_cancel(self.screen_my_info)
                self.detail_account_info_event_loop.exit()

        elif sRQName == '실시간미체결요청':
            rows = self.dynamicCall('GetRepeatCnt(Qstring, Qstring)', sTrCode, sRQName)
            for i in range(rows):
                code = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '종목코드')
                code_nm = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '종목명')
                order_no = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '주문번호')
                order_status = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '주문상태')
                order_quantity = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '주문수량')
                order_price = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '주문가격')
                order_type = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '주문구분')
                not_quantity = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '미체결수량')
                ok_quantity = self.dynamicCall('GetCommData(Qstring, Qstring, int, Qstring)', sTrCode, sRQName, i, '체결량')

                order_no = int(order_no.strip())
                if order_no in self.not_account_stock_list:
                    pass
                else:
                    self.not_account_stock_list[order_no] = {}

                self.not_account_stock_dict[code]['종목코드'] = code.strip()
                self.not_account_stock_dict[code]['종목명'] =  code_nm.strip()
                self.not_account_stock_dict[code]['주문상태'] = order_status.strip()
                self.not_account_stock_dict[code]['주문수량'] = int(order_quantity.strip())
                self.not_account_stock_dict[code]['주문가격'] = int(order_price.strip())
                self.not_account_stock_dict[code]['주문구분'] = order_type.strip().lstrip('+').lstrip('-')
                self.not_account_stock_dict[code]['미체결수량'] = int(not_quantity.strip())
                self.not_account_stock_dict[code]['미체결량'] = int(ok_quantity.strip())

            if sPrevNext == '2':
                self.not_concluded_account(sPrevNext='2')
            else:
                self.stop_screen_cancel(self.screen_my_info)
                self.detail_account_info_event_loop.exit()
                self.logger.info('self.detail_account_info_event_loop.exit()')

        elif sRQName == '주식일봉차트조회':
            code = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, 0, '종목코드')
            # data = self.dynamicCall('GetCommDataEx(QString, QString)', sTrCode, sRQName)
            cnt = self.dynamicCall('GetRepeatCnt(QString, QString)', sTrCode, sRQName)

            code = code.strip()

            for i in range(cnt):
                current_price = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '현재가')
                value = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '거래량')
                trading_value = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '거래대금')
                date = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '일자')
                start_price = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '시가')
                high_price = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '고가')
                low_price = self.dynamicCall('GetCommData(QString, QString, int, QString)', sTrCode, sRQName, i, '저가')

                data = [int(current_price.strip()), int(value.strip()), int(trading_value.strip()), date.strip(),
                        int(start_price.strip()), int(high_price.strip()), int(low_price.strip())]
                self.calcul_data.append(data.copy())

            if sPrevNext == '2':
                self.logger.info('sPrevNext: %s' %sPrevNext)
                self.day_kiwoom_db(code=code, sPrevNext=sPrevNext)
            else:
                self.strategy(code=code)
                self.calcul_data.clear()
                self.calculator_event_loop.exit()

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
            self.logger.info('%s: %s' % (sRealType, fid_mean))

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

            self.portfolio_stock_dict[sCode].update({'체결시간':date, '현재가':int(current_price), '전일대비':int(compared), '등락률':float(fluctuation),
                                                     '(최우선)매도호가':abs(int(ask)), '(최우선)매수호가':abs(int(bid)), '거래량':int(quantity), '누적거래량':abs(int(value)),
                                                     '고가':int(high_price), '시가':int(start_price), '저가':int(low_price)})

    def stop_screen_cancel(self, sScrNo=None):
        self.dynamicCall('DisconnectRealData(QString)', sScrNo)

    def get_account_info(self):
        account_list = self.dynamicCall('GetLoginInfo(QString)', 'ACCNO')
        self.logger.info('account_list : %s' %str(account_list))
        account_num = account_list.split(';')[0]

        self.account_num = account_num
        self.logger.info('계좌번호 : %s' %account_num)

    def detail_account_info(self, sPrevNext='0'):
        self.logger.info('detail_account_info')
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호', self.account_secret)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(QString, QString)', '조회구분', '3')
        self.dynamicCall('CommRqData(QString, QString, int, QString)', '예수금상세현황요청', 'opw00001', sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def detail_account_mystock(self, sPrevNext='0'):
        self.logger.info('detail_account_mystock')
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호', self.account_secret)
        self.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체구분', '00')
        self.dynamicCall('SetInputValue(QString, QString)', '조회구분', '1')
        self.dynamicCall('CommRqData(QString, QString, int, QString)', '계좌평가잔고내역요청', 'opw00018', sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def not_concluded_account(self, sPrevNext='0'):
        self.logger.info('not_concluded_account')
        self.dynamicCall('SetInputValue(QString, QString)', '계좌번호', self.account_num)
        self.dynamicCall('SetInputValue(QString, QString)', '매매구분', '0') # 매매구분 = 0:전체, 1:매도, 2:매수
        self.dynamicCall('SetInputValue(QString, QString)', '체결구분', '1') # 체결구분 = 0:전체, 2:체결, 1:미체결
        self.dynamicCall('CommRqData(QString, QString, int, QString)', '실시간미체결요청', 'opt10075', sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def get_code_list_by_market(self, market_name='코스닥'):
        code_list = self.dynamicCall('GetCodeListByMarket(QString)', self.market_code[market_name])
        code_list = code_list.split(';')[:-1]
        return code_list

    def day_kiwoom_db(self, code=None, date=None, sPrevNext='0'):
        QTest.qWait(5000)
        self.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
        self.dynamicCall('SetInputValue(QString, QString)', '수정주가부분', '1')
        if date is not None:
            self.dynamicCall('SetInputValue(QString, QString)', '기준일자', date)
        self.dynamicCall('CommRqData(QString, QString, int, QString)', '주식일봉차트조회', 'opt10081', sPrevNext, self.screen_calculation_stock)

        self.calculator_event_loop.exec_()

    def calculator_fnc(self):
        market_name = '코스닥'
        code_list = self.get_code_list_by_market(market_name=market_name)

        for idx, code in enumerate(code_list):
            self.dynamicCall('DisconnectRealData(QString)', self.screen_calculation_stock)
            self.logger.info('%s/%s : %s stock code: %s is updating' %(idx, len(code_list), market_name, code))
            self.day_kiwoom_db(code=code)
            if idx > 1000:
                break

    def strategy(self, code=None, movingPeriod=120, targetPeriod=3):   # moving 이동 평균선, target 관심 영역의 기간
        pass_success = False
        if self.calcul_data is None or len(self.calcul_data) < movingPeriod:
            pass_success = False
        else:
            total_price = 0
            for value in self.calcul_data[:movingPeriod]:
                total_price = total_price + value[0]
            moving_average_price = total_price / movingPeriod

            bottom_stock_price = False
            current_high_price = None
            if self.calcul_data[0][6] <= moving_average_price and moving_average_price <= self.calcul_data[0][5]: #low_price, high_price
                bottom_stock_price = True
                current_high_price = self.calcul_data[0][5]

            prev_low_price = None
            if bottom_stock_price:
                moving_average_price_prev = 0
                price_top_moving = False
                idx = 1

                while True:
                    if len(self.calcul_data[idx:]) < movingPeriod:
                        self.logger.info('there is no data for the period: %s' %movingPeriod)
                        break

                    for value in self.calcul_data[idx:movingPeriod + idx]:
                        total_price = total_price + value[0]
                    moving_average_price_prev = total_price / movingPeriod

                    if moving_average_price_prev <= int(self.calcul_data[idx][5]) and idx <= targetPeriod: # high price가 mvoing average 보다 높은 경우 fail
                        price_top_moving = False
                        break
                    elif (moving_average_price_prev < self.calcul_data[idx][6]) and idx > targetPeriod: # low price가 moving average 보다 높은 경구가 20일 전인 경우
                        self.logger.info('%s일치 이평선 위에 있는 구간 확인됨' %(movingPeriod))
                        price_top_moving = True
                        prev_low_price = self.calcul_data[idx][6]

                    idx = idx + 1

                if price_top_moving:
                    if moving_average_price > moving_average_price_prev and current_high_price > prev_low_price:
                        self.logger.info('이전 이평선 가격이 오늘자 이평선 가격보다 낮은 것 확인')
                        self.logger.info('이전 일봉 저가가 오늘자 일봉 고가보다 낮은지 확인')
                        pass_success = True

        if pass_success:
            self.logger.info('조건 통과')
            code_nm = self.dynamicCall('GetMasterCodeName(QString)', code)
            with open(self.condition_stock_path, 'a', encoding='utf-8') as f:
                f.write('%s\t%s\t현재가: %s\n' %(code, code_nm, str(self.calcul_data[0][0])))
                self.logger.info('%s\t%s\t현재가: %s\n' %(code, code_nm, str(self.calcul_data[0][0])))
        else:
            self.logger.info('조건 통과 못함')
            code_nm = self.dynamicCall('GetMasterCodeName(QString)', code)
            with open(self.condition_stock_path, 'a', encoding='utf-8') as f:
                f.write('%s\t%s\t현재가: %s\n' %(code, code_nm, str(self.calcul_data[0][0])))
                self.logger.info('%s\t%s\t현재가: %s\n' %(code, code_nm, str(self.calcul_data[0][0])))

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
                        self.portfolio_stock_dict.update({code: {'종목명': code_nm, '현재가': stock_price}})

    def screen_number_setting(self):
        screen_overwrite = []

        # 계좌평가잔고내역에 있는 종목들
        for code in self.account_stock_dict:
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for order_number in self.not_account_stock_dict:
            code = self.not_account_stock_dict[order_number]['종목코드']

            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 포트폴리오에 있는 종목들
        for code in self.portfolio_stock_dict:
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

            if code in self.portfolio_stock_dict:
                self.portfolio_stock_dict[code]['스크린번호'] = self.screen_real_stock
                self.portfolio_stock_dict[code]['주문용스크린번호'] = self.screen_meme_stock
            else:
                self.portfolio_stock_dict[code] = {'스크린번호':self.screen_real_stock, '주문용스크린번호':self.screen_meme_stock}

            cnt = cnt + 1

    def order(self, sCode, quantity, price, orderType='지정가'):
        order_success = self.dynamicCall('SendOrder(QString, QString, QString, int, QSting, int, int, QString, QString)', \
                        '신규매수', self.screen_meme_stock, self.account_num, 1, sCode, quantity, price, self.realType.SENDTYPE['거래부분'][orderType], '')
        if order_success:
            self.logger.info('매수주문 전달 성공')
        else:
            self.logger.info('매수주문 전달 실패')




