import os
import sys
import json
import re
try:
    from JiraTools import CookieTool
except Exception as e:
    pwd = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.dirname(pwd))
    from JiraTools import CookieTool

__cache = None


def get_cookie():
    return CookieTool.chrome_cookie()


def get_di(priority):
    '''
    根据 Jira 等级获取 Di 值
    '''
    config = load_config()
    return config['di'][priority.strip()]


def get_limit_days(priority):
    config = load_config()
    return config['limit_days'][priority.strip()]

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

    config = load_config()
    config['user']['username'] = username
    config['user']['password'] = password
    dump_config(config)


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
        else:
            print('invalid config_key >>>',args[0])
            exit(1)
    
    if username != None or password != None:
        set_user(username, password)


def isValidValue(value):
    return value != None and not value.startswith('-')

