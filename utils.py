import datetime

def paginate(page, per_page, count):
    offset = (page - 1) * per_page
    total_pages = int(count / per_page) + 1
    screen_pages = 10

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_page = (page - 1) // screen_pages * screen_pages + 1

    pages = []
    prev_num = start_page - screen_pages
    next_num = start_page + screen_pages

    if start_page - screen_pages > 0:
        has_prev = True
    else:
        has_prev = False
    if start_page + screen_pages > total_pages:
        has_next = False
    else:
        has_next = True
    if total_pages > screen_pages + start_page:
        for i in range(screen_pages):
            pages.append(i + start_page)
    elif total_pages < screen_pages:
        for i in range(total_pages):
            pages.append(i + start_page)
    else:
        for i in range(total_pages - start_page + 1):
            pages.append(i + start_page)
    paging = {'page':page,
              'has_prev':has_prev,
              'has_next':has_next,
              'prev_num':prev_num,
              'next_num':next_num,
              'count':count,
              'offset':offset,
              'pages':pages,
              'screen_pages':screen_pages,
              'total_pages':total_pages
              }
    return paging

def request_get(request_data):
    page = int(request_data.get('page', 1))
    keyword = request_data.get('kw', None)
    if keyword == '?':
        keyword = '\?'
    so = request_data.get('so', '1year')
    if so not in ['6month', '1year', '3year', '5year']:
        so = '1year'
    return page, keyword, so

def checkStockFinished():
    isStockFinished = False
    today = datetime.date.today()
    if today.weekday() == 5 or today.weekday() == 6:
        isStockFinished = True
    else:
        now = datetime.datetime.now()
        if now.hour < 8 or now.hour >= 16:
            isStockFinished = True
    return isStockFinished

def getDate(so='all'):
    today = datetime.date.today()
    if so == '6month':
        initialDate = today - datetime.timedelta(days=180)
    elif so == '3year':
        initialDate = today - datetime.timedelta(days=365 * 3)
    elif so == '5year':
        initialDate = today - datetime.timedelta(days=365 * 5)
    elif so == 'all':
        initialDate = today - datetime.timedelta(days=360 * 100)
    else:
        initialDate = today - datetime.timedelta(days=365)
    initialDate = initialDate.strftime("%Y%m%d")

    now = datetime.datetime.now()
    if today.weekday() == 5:
        today = today - datetime.timedelta(days=1)
    elif today.weekday() == 6:
        today = today - datetime.timedelta(days=2)
    elif now.hour < 8:
        today = today - datetime.timedelta(days=1)
    date = today.strftime("%Y%m%d")
    return date, initialDate


