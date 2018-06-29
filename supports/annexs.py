import getpass
import datetime
import threading
import sys, re, itertools, time, os

#附件下载
class EnvConfig:
    today = datetime.date.today().strftime(r'%Y-%m-%d')
    root_dir = None
    signal = False


def touch_link(user, link):

    if '/' not in link:
        link = f'http://jira.n.xiaomi.com/browse/{link}'

    html = user.session.get(link).text
    
    pattern_res_url = re.compile(r'<div class="attachment-thumb"><a href="(.*?)" draggable="true".*?<time.*?>(.*?)</time>')
    res_urls = pattern_res_url.findall(html)
    res_urls = list(dict.fromkeys(res_urls, 1).keys())

    res_urls = [list(x) for x in res_urls]
    
    for res in res_urls:
        times = res[1]
        if '/' in times:
            tmps = times.split(' ')
            
            dates = tmps[0].split('/')[::-1]
            datestr = convert_date(dates)

            res[1] = datestr + '/'+ ' '.join(tmps[1:][::-1])

    for res in res_urls:
        url = f"http://jira.n.xiaomi.com/{res[0]}"
        filepath = f"{EnvConfig.root_dir}/{link[link.rindex('/')+1:]}/{res[1]}"
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        filepath = f"{filepath}/{url[url.rindex('/')+1:]}"
        
        if not os.path.exists(filepath):
            filebytes = user.session.get(url) #下载文件资源地址，返回bit数据
            
            filebytes.raise_for_status() #检查状态
            with open(filepath, 'wb') as f:
                for chunk in filebytes.iter_content(204800):
                    f.write(chunk)  #将下载的文件从缓存写到磁盘路径上

            extract_file(filepath)


def extract_file(filepath):
    if filepath.endswith('.zip'):
        import zipfile
        zips = zipfile.ZipFile(filepath)

        if f"{filepath[filepath.rindex('/')+1:]}/".replace('.zip', '') in zips.namelist():
            zips.extractall(path=os.path.dirname(filepath))
        else:
            zips.extractall(path=filepath.replace('.zip', ''))
        zips.close()
    elif filepath.endswith('tar.gz'):
        import tarfile
        extract_dir = filepath.replace('.tar.gz', '')
        os.makedirs(extract_dir)

        tarfile = tarfile.open(filepath, 'r:gz')
        for file_name in tarfile.getnames():
            tarfile.extract(file_name, extract_dir)
        tarfile.close()

        extract_file(extract_dir)
    elif filepath.endswith('txt.gz'):
        import gzip
        extract_target = filepath.replace('.gz', '')
        gzips = gzip.GzipFile(filepath)
        open(extract_target, 'wb').write(gzips.read())
        gzips.close()
    elif os.path.isdir(filepath):
        for file in os.listdir(filepath):
            extract_file(f'{filepath}/{file}')
        


def touch_filter(user):
    filterstr = 'assignee = currentUser() AND status in (Reopen, "In Progress", reopend, Reopened, open) ORDER BY updated DESC'
    links = user.getJiraLinks(filterstr, 'all')

    for link in links:
        touch_link(user, link)


def wait_printer():   
    time.sleep(0.2)
    print('')
    write, flush = sys.stdout.write, sys.stdout.flush
    for dot in itertools.cycle([".  ", ".. ", "..."]):
        line = 'wait get all bugs '+dot
        write(line)
        flush()
        write('\x08' * len(line))
        time.sleep(0.6)

        if EnvConfig.signal:
            break
    write(' ' * len(line) + '\x08' * len(line))
    flush()


def convert_date(dates):
    year = '20'+dates[0]
    day = dates[2].ljust(2, '0')

    month = dates[1]
    if '一' in month or 'Jan' in month:
        month = '01'
    elif '二' in month or 'Feb' in month:
        month = '02'
    elif '三' in month or 'Mar' in month:
        month = '03'
    elif '四' in month or 'Apr' in month:
        month = '04'
    elif '五' in month or 'May' in month:
        month = '05'
    elif '六' in month or 'Jun' in month:
        month = '06'
    elif '七' in month or 'Jul' in month:
        month = '07'
    elif '八' in month or 'Aug' in month:
        month = '08'
    elif '九' in month or 'Sep' in month:
        month = '09'
    elif '十' in month or 'Oct' in month:
        month = '10'
    elif '十一' in month or 'Nov' in month:
        month = '11'
    elif '十二' in month or 'Dec' in month:
        month = '12'
    
    return year+'-'+month+'-'+day


def touch(user, link):

    EnvConfig.signal = False

    if getpass.getuser() == 'hujinqi':
        EnvConfig.root_dir = f'/home/{getpass.getuser()}/MIUI/jiras/{EnvConfig.today}'
    elif getpass.getuser() == 'weijuncheng':
        EnvConfig.root_dir = f'/home/{getpass.getuser()}/cts/MIUI/jiras/{EnvConfig.today}'

    spinner = threading.Thread(target=wait_printer)
    spinner.start()

    try:
        if link == 'all':
            touch_filter(user)
        else:
            touch_link(user, link)
    except Exception as e:
        print(e)
    finally:
        EnvConfig.signal = True
    
    spinner.join() #阻塞当前上下文环境的线程，直到调用此方法的线程终
    print(f'enjoy jiras in "{EnvConfig.root_dir}" :-)\n')