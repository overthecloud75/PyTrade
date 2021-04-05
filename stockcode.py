# https://ai-creator.tistory.com/51
import pandas as pd
from models import update_code

#해당 링크는 한국거래소에서 상장법인목록을 엑셀로 다운로드하는 링크입니다.
#다운로드와 동시에 Pandas에 excel 파일이 load가 되는 구조입니다.
stock_code = pd.read_html('http://kind.krx.co.kr/corpgeneral/corpList.do?method=download', header=0)[0]

# 데이터에서 정렬이 따로 필요하지는 않지만 테스트겸 Pandas sort_values를 이용하여 정렬을 시도해봅니다.
stock_code.sort_values(['상장일'], ascending=True)

# 필요한 것은 "회사명"과 "종목코드" 이므로 필요없는 column들은 제외
stock_code = stock_code[['회사명', '종목코드']]

# 한글 컬럼명을 영어로 변경
stock_code = stock_code.rename(columns={'회사명': 'codeName', '종목코드': 'code'})

# 종목코드가 6자리이기 때문에 6자리를 맞춰주기 위해 설정해줌
stock_code.code = stock_code.code.map('{:06d}'.format)
len_stock = len(stock_code)

for i in range(len_stock):
    update = {'codeName':stock_code.loc[i]['codeName'], 'code':stock_code.loc[i]['code']}
    update_code(update)