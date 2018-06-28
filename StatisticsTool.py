import re
import sys, itertools
import threading
import time


pages = None
issues = None
date_start = None
date_end = None


def statistics_core(user, index = 0):
    global pages
    global issues
    global date_start
    global date_end

    filterstr = f'created >= {date_start} AND created < {date_end} AND watcher in (hujinqi, weijuncheng) AND type = Bug ORDER BY  created ASC'

    params = {
        'startIndex':index,
        'filterId':-1,
        'jql':filterstr,
        'layoutKey': 'list-view'
    }

    headers = {
        'X-Atlassian-Token': 'no-check',
    }

    if index == 0:
        response = user.session.get('http://jira.n.xiaomi.com/issues/?filter=-1')
        if response.url != 'http://jira.n.xiaomi.com/issues/?filter=-1':
            printer.auth_error()
            exit(0)

    response = user.session.post('http://jira.n.xiaomi.com/rest/issueNav/1/issueTable', data=params, headers=headers)
        
    if response.status_code != 200:
        print(response.text)
        printer.auth_error()
        exit(1)

    html = response.text
    if index == 0:
        issues = list()
        pages = parse_pages(html)
    
    collect(html)
    

def parse_pages(html):
    totalPattern = re.compile(r'<span class=\\"results-count-total results-count-link\\">(.*?)</span>')
    total = int(totalPattern.search(html).group(1))
    
    count = int(total/50)

    indexs = list()
    for page in range(count+1)[1:]:
        indexs.append(page * 50)
    
    return indexs


def parse_issue(html):
    issue = {}

    # number
    issueKeyPattern = re.compile(r'<td class=\\"issuekey\\">.*?<a.*?>(.*?)</a>')
    issueKey = issueKeyPattern.search(html).group(1)
    issue['number'] = issueKey

    # desc
    issueSummaryPattern = re.compile(r'<td class=\\"summary\\">.*?<a.*?>(.*?)</a>')
    issueType = issueSummaryPattern.search(html).group(1).lower()
    if 'gsi' in issueType or 'vts' in issueType:
        issueType = 'VTS'
    elif 'gts' in issueType:
        issueType = 'GTS'
    elif 'cts' in issueType or 'verifier' in issueType:
        issueType = 'CTS'
    elif 'talkback' in issueType:
        issueType = 'TalkBack'
    else:
        issueType = 'OTHER'
    issue['type'] = issueType

    # priority
    issuePriorityPattern = re.compile(r'<td class=\\"priority\\">.*?<img.*?title=\\"(.*?)\\">')
    issuePriority = issuePriorityPattern.search(html).group(1)
    if 'Critical' in issuePriority:
        issuePriority = 'Critical'
    elif 'Blocker' in issuePriority:
        issuePriority = 'Blocker'
    elif 'Major' in issuePriority:
        issuePriority = 'Major'
    elif 'Minor' in issuePriority:
        issuePriority = 'Minor'
    elif 'Trivial' in issuePriority:
        issuePriority = 'Trivial'
    else:
        issuePriority = 'X'
    issue['priority'] = issuePriority

    # status
    issueStatusPattern = re.compile(r'<td class=\\"status\\">.*?<span.*?>(.*?)</span>')
    issueStatus = issueStatusPattern.search(html).group(1)
    issue['status'] = issueStatus

    return issue

def collect(html):
    global issues

    issueRowPattern = re.compile(r'<tr id=\\"(.+?)\\" rel=\\"(.+?)\\" data-issuekey=\\"(.+?)\\" class=\\"(.+?)\\">(.+?)</tr>')
    issue_rows = issueRowPattern.findall(html)
    for issue_row in issue_rows:
        tmp = issue_row[4]
        issues.append(parse_issue(tmp))


def output():
    cts = {
        'number':0,
        'critical':0,
        'blocker':0,
        'major':0,
        'minor':0,
        'trivial':0
    }
    vts = dict(cts)
    gts = dict(cts)
    talkback = dict(cts)

    other = dict(cts)
    other['jira'] = list()


    total = dict(cts)
    percent = dict(cts)

    for issue in issues:

        cur = None
        if issue['type'] == 'VTS':
            cur = vts
        elif issue['type'] == 'CTS':
            cur = cts
        elif issue['type'] == 'GTS':
            cur = gts
        elif issue['type'] == 'TalkBack':
            cur = talkback
        else:
            cur = other
            cur['jira'].append(issue['number'])
        
        cur['number'] += 1
        cur[issue['priority'].lower()] += 1

        total['number'] += 1
        total[issue['priority'].lower()] += 1

    tab = ''.ljust(10)
    column = 'casttype'+tab+'blocker'+tab+'critical'+tab+'major'+tab+'minor'+tab+'trivial'+tab+'total '

    global date_start
    global date_end

    import datetime
    dates = date_end.split('-')
    tmp_date_end = datetime.date(year=int(dates[0]), month=int(dates[1]), day=int(dates[2]))
    tmp_date_end = tmp_date_end + datetime.timedelta(days=-1)
    tmp_date_end = tmp_date_end.strftime(r'%Y-%m-%d')

    if date_start != tmp_date_end:
        print(f' >>> {date_start}~{tmp_date_end} <<< '.center(len(column), "*"))
    else:
        print(f' >>> {date_start} <<< '.center(len(column), "*"))
    print('')
    print(column)

    cts_desc = format_desc(cts, 'cts')
    gts_desc = format_desc(gts, 'gts')
    vts_desc = format_desc(vts, 'vts')
    talkback_desc = format_desc(talkback, 'talkback')
    other_desc = format_desc(other, 'other')

    print(cts_desc)
    print(gts_desc)
    print(vts_desc)
    print(talkback_desc)
    print(other_desc)

    line = "*"*len(column)
    total_desc = format_desc(total, 'total')

    percent['blocker'] = "%.3f"%(total['blocker'] / total['number'])
    percent['critical'] = "%.3f"%(total['critical'] / total['number'])
    percent['major'] = "%.3f"%(total['major'] / total['number'])
    percent['minor'] = "%.3f"%(total['minor'] / total['number'])
    percent['trivial'] = "%.3f"%(total['trivial'] / total['number'])
    percent['number'] = '1.00'

    percent_desc = format_desc(percent, 'percent')

    print('')
    print(line)
    print('')
    print(total_desc)
    print(percent_desc)
    print('')

    if len(other['jira']) > 0:
        print(' >>> other <<< '.center(len(column), "*"))
        print('')
        for item in other['jira']:
            print(f'http://jira.n.xiaomi.com/browse/{item}')
        print('')

def format_desc(data, key):
    tab = ''.ljust(10)
    string = key.ljust(8)+\
            tab+str(data['blocker']).ljust(7)+\
            tab+str(data['critical']).ljust(8)+\
            tab+str(data['major']).ljust(5)+\
            tab+str(data['minor']).ljust(5)+\
            tab+str(data['trivial']).ljust(7)+\
            tab+str(data['number']).ljust(5)

    return string


signal = False
def wait_printer():
    global signal   
    write, flush = sys.stdout.write, sys.stdout.flush
    for dot in itertools.cycle([".  ", ".. ", "..."]):
        line = 'wait get all bugs '+dot
        write(line)
        flush()
        write('\x08' * len(line))
        time.sleep(0.6)

        if signal:
            break
    write(' ' * len(line) + '\x08' * len(line))
    flush()


def check_get_status(user):
    global signal

    statistics_core(user, 0)

    while (pages != None and len(pages) > 0):
        index = pages.pop(0)
        statistics_core(user, index)
    signal = True
    
def statistics(user, p_date_start, p_date_end):
    global signal
    global date_start
    global date_end
    print('')
    date_start = p_date_start
    date_end = p_date_end
    signal = False
    spinner = threading.Thread(target=wait_printer)
    spinner.start()
    check_get_status(user)
    spinner.join()
    output()
    