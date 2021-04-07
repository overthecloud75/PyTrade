def errors(err_code):

    err_dic = {0:'정상처리',
               10:'실패',
               100:'사용자정보교환실패',
               101:'서버접속실패',
               106:'통신연결종료'
               }
    result = err_dic[err_code]
    return result