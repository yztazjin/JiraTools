#! /home/linuxbrew/.linuxbrew/bin/python3

import requests
from requests_html import HTML
import re
import sys
import os
import json
import datetime

pwd = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(pwd))
    
from JiraTools.config import Config
from JiraTools import printer
from JiraTools import StatisticsTool
from JiraTools.supports import annexs
from JiraTools.supports import models


class JIRAUser:

    
    def __init__(self):
        
        self.session = requests.session()
        del self.session.headers['User-Agent'] 
        
        self.__isAuthed = False

        self.username = None
        self.password = None


    def loginAuth(self):
        '''
        登录
        '''
        auth_cookie = Config.get_cookie()
        # use cookie to login
        if auth_cookie != None and auth_cookie.strip() != '':
            
            # requests session will auto manage cookies for us just like a browser
            self.session.cookies.clear()
            for cookie in auth_cookie.split(';'):
                key, value = cookie.split('=', 1)
                self.session.cookies.set(key.strip(), value.strip())

            response = self.session.post('https://cas.mioffice.cn/login')
            if response.status_code == 200:
                self.__isAuthed = 'con-f-success' in response.text
                if self.isAuthed:
                    return self
            
            print('invalid cookie, maybe need to update')
        
        # use username password to login
        if self.password is None \
            or self.username is None:
            printer.auth_error()
            exit(1)
        
        headers = {
            'Content-Type':'application/x-www-form-urlencoded'
        }

        response = self.session.post('https://cas.mioffice.cn/login', headers = headers)
        html = HTML(html=response.text)

        login_params = {}
        login_params['username'] = self.username
        login_params['password'] = self.password
        login_params['mi_service'] =  html.lxml.body.forms[0].inputs.form[2].value
        login_params['lt'] =  html.lxml.body.forms[0].inputs.form[3].value
        login_params['execution'] =  html.lxml.body.forms[0].inputs.form[4].value
        login_params['_eventId'] = html.lxml.body.forms[0].inputs.form[5].value
        login_params['rememberMe'] = 'on'

        response = self.session.post('https://cas.mioffice.cn/login', headers=headers, params=login_params)
        if response.status_code == 200:
            self.__isAuthed = 'con-f-success' in response.text

        return self


    @property
    def isAuthed(self):
        return self.__isAuthed


    def getJiraLinks(self, filterstr, type):
        '''
        type: 'odm', 'miui', 'all', 'show'
        '''
        if not self.isAuthed:
            raise Exception('not login')
            
        params = {
            'startIndex':0,
            'filterId':-1,
            'jql':filterstr,
            'layoutKey': 'list-view'
        }

        headers = {
            'X-Atlassian-Token': 'no-check',
        }
        
        print('\n','filter >>> %s'%filterstr, sep='')
        # no-check
        response = self.session.get('http://jira.n.xiaomi.com/issues/?filter=-1')
        if response.url != 'http://jira.n.xiaomi.com/issues/?filter=-1':
            printer.auth_error()
            exit(0)

        response = self.session.post('http://jira.n.xiaomi.com/rest/issueNav/1/issueTable', data=params, headers=headers)
        
        if response.status_code != 200:
            print(response.text)
            printer.auth_error()
            exit(1)

        html = HTML(html=response.text)

        jira_links = [x for x in html.links if x.startswith('/browse')]
        miui_jira_links = [x for x in jira_links if x.startswith('/browse/MIUI')]
        plt_jira_links = [x for x in jira_links if not x.startswith('/browse/MIUI')]

        if type == 'all':
            return ['http://jira.n.xiaomi.com'+x for x in jira_links]
        elif type == 'odm':
            return ['http://jira.n.xiaomi.com'+x for x in plt_jira_links]
        elif type == 'miui':
            return ['http://jira.n.xiaomi.com'+x for x in miui_jira_links]
        elif type == 'show':
            dis = 0
            total = 0

            print('\n',' cts/gts/vts '.center(102, "*"), '\n', sep='')
            links = ['http://jira.n.xiaomi.com'+x for x in jira_links]
            for link in links:
                total += 1
                dis += self.printBuglist(link)

            if total == 0:
                print('Empty Jiras :-)'.center(102, " "))
            
            print('\n', ' summary '.center(102, "*"), '\n', sep='')

            summary = ('>>> total %d di %d <<<\n'%(total, dis)).center(102)
            print(summary)
            return []
        else:
            return []


    def printBuglist(self, url):
        '''
        just show jira infos
        '''
        if not self.isAuthed:
            raise Exception('not login')

        html = self.session.get(url).text
        searcher = re.search(r'<dl>(.*?)</dl>', html, re.S)
        owner_line = searcher.group(1)
        searcher = re.search(r'</span></span>(.*?)</span>', owner_line, re.S)
        ownername = searcher.group(1).strip()
        # searcher = re.search(r'displayName&quot;:&quot;[0-9a-zA-Z ]*([^a-zA-Z]*?)&quot;', html)
        # ownername = searcher.group(1)
        space_num = ownername.count(' ')
        ownername = ownername + ' '*(10-len(ownername)+space_num) + ' '*(10-len(ownername))

        searcher = re.search(r'<span id="priority-val".*?title="(.*?)".*?/>', html, re.S)
        if searcher is None:
            print("Didn't find the priority, maybe something wrong with server, just try again")
            exit(1)
        priority = searcher.group(0)
        if 'Critical' in priority:
            priority = 'Critical'.ljust(17)
        elif 'Blocker' in priority:
            priority = 'Blocker'.ljust(17)
        elif 'Major' in priority:
            priority = 'Major'.ljust(17)
        elif 'Minor' in priority:
            priority = 'Minor'.ljust(17)
        elif 'Trivial' in priority:
            priority = 'Trivial'.ljust(17)
        else:
            print('did not find priority >>>', priority)
            priority = 'X'

        searcher = re.search(r'<span[^<]+?id="created-val".*?</span>', html, re.S)
        searcher = re.search(r'datetime="(.*?)"', searcher.group(0))
        create_date = searcher.group(1).split('T')[0]
        create_date = datetime.datetime.strptime(create_date, "%Y-%m-%d")
        today_date = datetime.datetime.today()
      
        diff = today_date - create_date
        limit_days = Config.get_limit_days(priority)
        if limit_days > 0:
            left_days = limit_days - diff.days

            days_desc = create_date
            if left_days > 0:
                days_desc = "未超期 %3d 天"%left_days
            elif left_days == 0:
                days_desc = "未超期   0 天"
            else:
                left_days = -left_days
                days_desc = "已超期 %3d 天"%left_days
        else:
            days_desc = ''

        print(url.ljust(48), priority, ownername, days_desc)

        return Config.get_di(priority)


    def updateComponents(self, url):
        '''
        更新 Jira 的 Component
        '''
        if not self.isAuthed:
            raise Exception('not login')

        JIRANumber = url.replace('http://jira.n.xiaomi.com/browse/','').ljust(15)

        html = self.session.get(url).text
        searcher = re.search(r'issueId=([0123456789]+)', html)
        issueId = searcher.group(1)

        searcher = re.search(r'atl_token=(.*?)"', html)
        atl_token = searcher.group(1)

        searcher = re.search(r'<span id="assignee-val" class="view-issue-field">(.*?)</span>', html, re.S)
        searcher = re.search(r'([^;]*?@.*?\.com)', searcher.group(1))
        email = searcher.group(1)

        searcher = re.search(r'displayName&quot;:&quot;[0-9a-zA-Z ]*([^a-zA-Z]*?)&quot;', html)
        ownername = searcher.group(1)
        ownername = ownername + '  '*(5-len(ownername))

        components = list()
        searcher = re.search(r'<span class="shorten" id="components-field">(.*?)</span>', html, re.S)
        if searcher:
            text = searcher.group(1).strip()
            for tmp in text.split(','):
                searcher = re.search(r'>(.*?)<', tmp)
                components.append(searcher.group(1))

        pattern = re.compile(r'.*@(.*)\.com')
        host = pattern.match(email).group(1)

        params = {
                'atl_token':atl_token,
                'singleFieldEdit':'true',
                'fieldsToForcePresent':'components',
                'issueId':issueId
        }

        owners = Config.get_owners()
        if host == 'xiaomi':

            if JIRANumber.startswith('MIUI'):
                owner = owners.get(email)
                if owner != None:
                    params['components'] = owner['value']
            else:
                print(url.ljust(48), ownername, 'ignore >>> plt bug but miui owner ... ')
                return
        elif len(components) > 1:
            # 多个 Compoents 暂时不处理
            print(url.ljust(48), ownername, 'ignore >>> compoents > 1 ... ')
            return
        else:
            # Update Component To ODM Platform
            owner = owners.get(host)
            if owner != None:
                params['components'] = owner['value']
        
        if params.get('components') != None:
            # 更新 JIRA Component 的接口
            update_intf = 'http://jira.n.xiaomi.com/secure/AjaxIssueAction.jspa?decorator=none'
            response = self.session.post(update_intf, data=params)
            if response.status_code == 200:
                print(url.ljust(48), ownername, 'setted >>> [',owner['title'],']')
        else:
            print(url.ljust(48), ownername, 'ignore >>> unknown owner ...')


def convertArgs():
    '''
    show  [cts-other, cts-self, cts-all, statistics]
    set   -u [username] -p [password] -c [cookie]
    trans [miui, odm, all]
    touch [all, jira link]
    '''
    input_args = sys.argv[1:]

    if len(input_args) < 1:
        return ['show', 'statistics']

    return input_args


def main():
    args = convertArgs()

    if args[0] == '--help':
        print('\n', ' help '.center(75, "*"), '\n', sep='')
        print(' show  [cts-other, cts-self, cts-all, statistics] 展示JIRA')
        print(' set -u [username] -p [password]')
        print(' trans [miui, odm, all] 分配模块')
        print(' touch [all, jira link]')
        print(' chrome browser >>> https://cas.mioffice.cn/login to refresh chrome-cookie')
        print('\n', '*'*75, '\n', sep='')
        exit(0)

    if args[0] == 'set':
        Config.set_config_from_args(args[1:])
        exit(0)


    username, password = Config.get_user()
    user = JIRAUser()
    user.username = username
    user.password = password
    user.loginAuth()

    if not user.isAuthed:
        print('login failed')
        exit(1)
    if args[0] == 'show':

        if args[1] == 'statistics':
            import datetime
            date_today = datetime.date.today()

            date_start = date_today + datetime.timedelta(days=-90)
            date_start = date_start.strftime(r'%Y-%m-%d')

            date_end = date_today + datetime.timedelta(days=1)
            date_end = date_end.strftime(r'%Y-%m-%d')

            if len(args) > 2:
                date_start = args[2]
            if len(args) > 3:
                date_end = args[3]
                dates = date_end.split('-')
                date_end = datetime.date(year=int(dates[0]), month=int(dates[1]), day=int(dates[2]))
                date_end = date_end + datetime.timedelta(days=1)
                date_end = date_end.strftime(r'%Y-%m-%d')
                
            StatisticsTool.statistics(user, date_start, date_end)
        else:
            filterstr = Config.get_filter(args[1])
            if filterstr == None:
                print('error filter option')
                exit(1)
        
            user.getJiraLinks(filterstr, 'show')
    elif args[0] == 'trans':
        typestr = args[1]
        filterstr = Config.get_filter('cts-other')

        if typestr not in ['miui', 'odm', 'all']:
            print('error type option')
            exit(1)

        for link in user.getJiraLinks(filterstr, typestr):
            user.updateComponents(link)
    elif args[0] == 'touch':
        link = args[1]
        annexs.touch(user, link)
    elif args[0] == 'whats':
        argument = args[1]
        models.todo(user, argument)
    else:
        print('invalid params')
        exit(1)


if __name__ == '__main__':
    main()
    