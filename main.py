from kiwoom.kiwoom import *
import sys
from PyQt5.QtWidgets import *
import logging
import logging.handlers
from datetime import datetime

class Main():
    def __init__(self):

        self.logger = self.set_logger()
        self.logger.info('Main start')

        self.app = QApplication(sys.argv)
        self.kiwoom = Kiwoom()
        self.app.exec_()

    def set_logger(self):  # 로그 환경을 설정해주는 함수
        logger = logging.getLogger()
        fomatter = logging.Formatter('[%(levelname)s|%(lineno)s] %(asctime)s > %(message)s')  # 로그를 남길 방식으로 "[로그레벨|라인번호] 날짜 시간,밀리초 > 메시지" 형식의 포매터를 만든다
        logday = datetime.today().strftime("%Y%m%d")  # 로그 파일 네임에 들어갈 날짜를 만듬 (YYYYmmdd 형태)

        fileMaxByte = 1024 * 1024 * 100  # 파일 최대 용량인 100MB를 변수에 할당 (100MB, 102,400KB)
        fileHandler = logging.handlers.RotatingFileHandler('./log/stock_' + str(logday) + '.log', maxBytes=fileMaxByte,
                                                           backupCount=10)  # 파일에 로그를 출력하는 핸들러 (100MB가 넘으면 최대 10개까지 신규 생성)
        streamHandler = logging.StreamHandler()  # 콘솔에 로그를 출력하는 핸들러

        fileHandler.setFormatter(fomatter)  # 파일에 로그를 출력하는 핸들러에 포매터를 지정
        streamHandler.setFormatter(fomatter)  # 콘솔에 로그를 출력하는 핸들러에 포매터를 지정

        logger.addHandler(fileHandler)  # 로그 인스턴스에 파일에 로그를 출력하는 핸들러를 추가
        logger.addHandler(streamHandler)  # 로그 인스턴스에 콘솔에 로그를 출력하는 핸들러를 추가

        logger.setLevel(logging.DEBUG)

        return logger

if __name__ == '__main__':
    Main()



