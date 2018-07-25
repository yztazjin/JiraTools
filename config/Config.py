import os
import sys
import json
import re


__cache = None


def get_cookie():
    try:
        from JiraTools import CookieTool
    except Exception:
        pwd = os.path.dirname(os.path.abspath(__file__))
        pwd = os.path.dirname(pwd)
        pwd = os.path.dirname(pwd)
        sys.path.append(pwd)
        from JiraTools import CookieTool

    return CookieTool.chrome_cookie()


def get_di(priority):
    '''
    根据 Jira 等级获取 Di 值
    '''
    config = load_config()
    return config['di'].get(priority.strip(), 0)


def get_limit_days(priority):
    config = load_config()
    return config['limit_days'].get(priority.strip(), -1)

def get_user():
    '''
    获取用户名/密码
    '''
    config = load_config()
    return (config['user'].get('username'), config['user'].get('password'))


def get_filter(key):
    '''
    获取 Jira Filter
    '''
    config = load_config()
    return config['filter'].get(key)


def set_user(username, password):
    '''
    持久化用户名/密码
    '''
    if username == None or password == None:
        print('username, password cannot set only one')
        return

    config = load_config()
    config['user']['username'] = username
    config['user']['password'] = password
    dump_config(config)
    print('username, password set success')


def set_filter(fk, fe):
    '''
    持久化自定义 filter
    '''
    if fk == None or fe == None:
        print('filter_key, filter_expression cannot set only one')
        return

    config = load_config()
    config['filter'][fk] = fe
    dump_config(config)
    print('filter_key, filter_expression set success')


def load_config():
    '''
    load config to runtime memory
    '''
    global __cache 
    if __cache != None:
        return __cache
    
    path = '%s/config.json'%os.path.dirname(os.path.abspath(__file__))

    __cache = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            __cache = json.load(f)
    
    if __cache.get('di') == None:
        __cache['di'] = {
            'Critical':5,
            'Blocker':10,
            'Major':1,
            'Minor':0.1
        }
    
    if __cache.get('limit_days') == None:
        __cache['limit_days'] = {
            'Critical':15,
            'Blocker':7,
            'Major':120,
            'Minor':180
        }
    
    if __cache.get('filter') == None:
        __cache['filter'] = {
            'cts-other':'status in (open, "In Progress", Reopened, Reopen, reopend) AND component = "系统稳定性-CTS/GTS" AND assignee not in (weijuncheng, hujinqi) AND type in (Bug, 线上BUG) ORDER BY updated DESC',
            'cts-self': 'assignee in (weijuncheng, hujinqi) And type in (线上BUG, Bug) And status in (open, "In Progress", Reopened, Reopen, reopend) ORDER BY updated DESC',
            'cts-all': 'status in (open, "In Progress", Reopened, Reopen, reopend) AND component = "系统稳定性-CTS/GTS" AND type in (Bug, 线上BUG) ORDER BY updated DESC'
        }

    if __cache.get('user') == None:
        __cache['user'] = {}

    if __cache.get('cookie_update_flag') == None:
        __cache['cookie_update_flag'] = 0

    return __cache


def dump_config(config):
    '''
    持久化到文件
    '''
    path = '%s/config.json'%os.path.dirname(os.path.abspath(__file__))

    with open(path, 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def get_owners():
    '''
    owners 文件配置表
    '''
    path = '%s/dicts.json'%os.path.dirname(os.path.abspath(__file__))
    with open(path, 'r') as f:
        return json.load(f)
    
    return {}


def set_config_from_args(args):
    username = None
    password = None
    filter_key = None
    filter_expr = None

    if len(args) < 1 or len(args) % 2 != 0:
        print('invalid args >>>',args)
        exit(1)

    while len(args) > 0:
        if args[0] == '-u':
            username = args[1]
            if isValidValue(username):
                
                args = args[2:]
            else:
                print('invalid config_value username >>>',args[1])
                exit(1)

        elif args[0] == '-p':
            password = args[1]
            if isValidValue(password):
                
                args = args[2:]
            else:
                print('invalid config_value password >>>',args[1])
                exit(1)

        elif args[0] == '-fk':
            filter_key = args[1]
            if isValidValue(filter_key):
                args = args[2:]
            else:
                print('invalid config_value filter key word >>>',args[1])
                exit(1)

        elif args[0] == '-fe':
            filter_expr = args[1]
            if isValidValue(filter_expr):
                
                args = args[2:]
            else:
                print('invalid config_value filter expression >>>',args[1])
                exit(1)

        else:
            print('invalid config_key >>>',args[0])
            exit(1)
    
    if username != None or password != None:
        set_user(username, password)
    
    if filter_key !=None or filter_expr !=None:
        set_filter(filter_key, filter_expr)


def isValidValue(value):
    return value != None and not value.startswith('-')


def get_to_owner(jira, html):
    html = html.lower()

    import re
    # body = re.search(r'<body.*?>(.*?)</body>', html, re.S).group(1)
    title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)

    to_owner = None
    if 'camera' in title:
        if 'HTH' in jira:
            # 龙旗
            to_owner = 'p-mawenke'
        elif 'MIUI' in jira:
            # MIUI
            to_owner = 'zhanghaipo'
        elif 'HONGMI' in jira:
            # 闻泰
            to_owner = 'p-sunli6'
        elif 'HQ' in jira:
            # 华勤
            to_owner = 'v-zhangruijie'

    elif 'media' in title or 'audio' in title or 'video' in title:
        if 'HTH' in jira:
            # 龙旗
            to_owner = 'p-mawenke'
        elif 'MIUI' in jira:
            # MIUI
            to_owner = 'xiongdawei'
        elif 'HONGMI' in jira:
            # 闻泰
            to_owner = 'p-sunli6'
        elif 'HQ' in jira:
            # 华勤
            to_owner = 'v-zhangruijie'
    
    return to_owner

def get_owner_components_value(owner):
    if owner == 'xiongdawei':
        # Media Audio Video
        return '17396'
    elif owner == 'zhanghaipo':
        # Camera
        return '17394'
    elif owner == 'p-sunli6':
        # 闻泰
        return '13455'
    elif owner == 'v-zhangruijie':
        # 华勤
        return '15835'
    elif owner == 'p-mawenke':
        # 龙旗
        return '13460'