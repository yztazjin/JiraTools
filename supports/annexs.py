import getpass
import datetime
import threading
import sys, re, itertools, time, os, zipfile


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
    
    for res in res_urls:
        url = f"http://jira.n.xiaomi.com/{res[0]}"
        filepath = f"{EnvConfig.root_dir}/{link[link.rindex('/')+1:]}"
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        filepath = f"{filepath}/{url[url.rindex('/')+1:]}"
        
        if not os.path.exists(filepath):
            filebytes = user.session.get(url)
            
            filebytes.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in filebytes.iter_content(204800):
                    f.write(chunk)
        
            if filepath.endswith('.zip'):
                zips = zipfile.ZipFile(filepath)

                if f"{url[url.rindex('/')+1:]}/".replace('.zip', '') in zips.namelist():
                    zips.extractall(path=os.path.dirname(filepath))
                else:
                    zips.extractall(path=filepath.replace('.zip', ''))


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


def touch(user, link):

    EnvConfig.signal = False

    if getpass.getuser() == 'hujinqi':
        EnvConfig.root_dir = f'/home/{getpass.getuser()}/MIUI/jiras/{EnvConfig.today}'

    spinner = threading.Thread(target=wait_printer)
    spinner.start()

    if link == 'all':
        touch_filter(user)
    else:
        touch_link(user, link)

    EnvConfig.signal = True
    spinner.join()
    print(f'enjoy jiras in "{EnvConfig.root_dir}" :-)\n')