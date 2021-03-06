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

        try:
            html = self.session.get(url).text
            searcher = re.search(r'displayName&quot;:&quot;[0-9a-zA-Z ]*([^a-zA-Z]*?)&quot;', html)
            ownername = searcher.group(1)
            space_num = ownername.count(' ')
            ownername = ownername + ' '*(10-len(ownername)+space_num) + ' '*(10-len(ownername))

            searcher = re.search(r'<span id="priority-val".*?title="(.*?)".*?/>', html, re.S)
            priority = searcher.group(0)
        except Exception as e:
            print("Parse jira_html fail, maybe something wrong with server, just try again")
            exit(1)

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

        try:
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
        except Exception as e:
            print("Parse jira_html fail, maybe something wrong with server, just try again")
            exit(1)

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


    def startWatch(self, url):
        '''
        add watcher
        '''
        if not self.isAuthed:
            raise Exception('not login')
        
        try:
            html = self.session.get(url).text
            searcher = re.search(r'issueId=([0123456789]+)', html)
            issueId = searcher.group(1)

            searcher = re.search(r'displayName&quot;:&quot;[0-9a-zA-Z ]*([^a-zA-Z]*?)&quot;', html)
            ownername = searcher.group(1)
            ownername = ownername + '  '*(5-len(ownername))
        except Exception as e:
            print("Parse jira_html fail, maybe something wrong with server, just try again")
            exit(1)

        jira_number = url.replace('http://jira.n.xiaomi.com/browse/','')
        post_url = f'http://jira.n.xiaomi.com/rest/api/1.0/issues/{issueId}/watchers'

        params = {
            'dummy':'true'
        }
        header = {
            'Content-Type': 'application/json'
        }
        response = self.session.post(post_url, data=json.dumps(params), headers=header)
        if response.status_code == 200:
            print(url.ljust(48), ownername, 'watched success')
        else:
            print(url.ljust(48), ownername, 'watched fail')
    

    def dispatch(self, url):
        '''
        dispatch and add comment
        '''
        if not self.isAuthed:
            raise Exception('not login')
        
        jira_number = url.replace('http://jira.n.xiaomi.com/browse/','')

        to_ownername = 'weijuncheng'

        try:
            html = self.session.get(url).text
            to_ownername = Config.get_to_owner(jira_number, html)

            if to_ownername == None:
                print(url.ljust(48), f'dispatch not needed')
                return

            searcher = re.search(r'issueId=([0123456789]+)', html)
            issueId = searcher.group(1)

            searcher = re.search(r'atl_token=(.*?)"', html)
            atl_token = searcher.group(1)

        except Exception as e:
            print("Parse jira_html fail, maybe something wrong with server, just try again")
            exit(1)

        # 添加评论
        header = {
            'Content-Type': 'application/json'
        }
        params = {
            'body': f'[~{to_ownername}] 麻烦帮忙看下这个问题吧，谢谢。'
        }
        post_comment_url = f'http://jira.n.xiaomi.com/rest/api/2/issue/{jira_number}/comment'
        response = self.session.post(post_comment_url, data=json.dumps(params), headers=header)
        if response.status_code !=200 and response.status_code != 201:
            print(url.ljust(48), 'add comment fail')
            exit(1)

        # 修改 component
        params = {
            'atl_token':atl_token,
            'singleFieldEdit':'true',
            'fieldsToForcePresent':'components',
            'issueId':issueId,
            'components': Config.get_owner_components_value(to_ownername)
        }
        post_components_url = 'http://jira.n.xiaomi.com/secure/AjaxIssueAction.jspa?decorator=none'
        response = self.session.post(post_components_url, data=params)
        if response.status_code !=200 and response.status_code != 201:
            print(url.ljust(48), 'set components fail')
            exit(1)

        # 转移 owner
        params = {
            'assignee': to_ownername,
            'issueId': issueId,
            'atl_token': atl_token,
            'singleFieldEdit': 'true',
            'fieldsToForcePresent': 'assignee'
        }
        post_assigne_url = 'http://jira.n.xiaomi.com/secure/AjaxIssueAction.jspa?decorator=none'
        response = self.session.post(post_assigne_url, data=params)
        if response.status_code == 200:
            print(url.ljust(48), f'dispatch to {to_ownername} success')
        else:
            print(url.ljust(48), f'dispatch to {to_ownername} fail')


    def dispatch_owner(self, url, owner):
        '''
        指定owner
        '''
        if not self.isAuthed:
            raise Exception('not login')

        jira_number = url.replace('http://jira.n.xiaomi.com/browse/','')

        try:
            html = self.session.get(url).text
            to_ownername = owner

            searcher = re.search(r'issueId=([0123456789]+)', html)
            issueId = searcher.group(1)

            searcher = re.search(r'atl_token=(.*?)"', html)
            atl_token = searcher.group(1)

        except Exception as e:
            print("Parse jira_html fail, maybe something wrong with server, just try again")
            exit(1)
        
        # 添加评论
        header = {
            'Content-Type': 'application/json'
        }
        params = {
            'body': f'[~{to_ownername}] 麻烦帮忙看下这个问题吧，谢谢。'
        }
        post_comment_url = f'http://jira.n.xiaomi.com/rest/api/2/issue/{jira_number}/comment'
        response = self.session.post(post_comment_url, data=json.dumps(params), headers=header)
        if response.status_code !=200 and response.status_code != 201:
            print(url.ljust(48), 'add comment fail')
            exit(1)

        # 转移 owner
        params = {
            'assignee': to_ownername,
            'issueId': issueId,
            'atl_token': atl_token,
            'singleFieldEdit': 'true',
            'fieldsToForcePresent': 'assignee'
        }
        post_assigne_url = 'http://jira.n.xiaomi.com/secure/AjaxIssueAction.jspa?decorator=none'
        response = self.session.post(post_assigne_url, data=params)
        if response.status_code == 200:
            print(url.ljust(48), f'dispatch to {to_ownername} success')
        else:
            print(url.ljust(48), f'dispatch to {to_ownername} fail')

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
        print(' show         [cts-other, cts-self, cts-all, statistics] 展示JIRA')
        print(' set -u       [username] -p [password]')
        print(' set -fk      [key word] -fe [filter expression] 设置自定义filter')
        print(' trans        [miui, odm, all] 分配模块')
        print(' dispatch     [jira link, jira filter, filter brief] 转交 jira owner')
        print(' touch        [all, jira link] 生成 jira 工作目录')
        print(' watch        [jira link, jira filter, filter brief] 关注 jiras')
        print(' whats        [model key workd] 根据关键字获取手机信息')
        print(' random       [jira link, jira filter, filter brief] random dispatch')
        print('\n chrome browser >>> https://cas.mioffice.cn/login to refresh chrome-cookie')
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

    if args[0] == 'show' and args[1] != None:

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
                if 'jira.n.xiaomi.com/browse' in args[1]:
                    user.printBuglist(args[1])
            elif ' ' in args[1]:
                filterstr = args[1]

            if filterstr != None:
                user.getJiraLinks(filterstr, 'show')
            else:
                print('expect for a valid filter expression')

    elif args[0] == 'trans' and args[1] != None:
        typestr = args[1].strip()
        filterstr = Config.get_filter('cts-other')

        if typestr not in ['miui', 'odm', 'all']:
            print('error type option')
            exit(1)

        for link in user.getJiraLinks(filterstr, typestr):
            user.updateComponents(link)

    elif args[0] == 'touch':
        link = args[1]
        annexs.touch(user, link)

    elif args[0] == 'whats' and args[1] != None:
        argument = args[1]
        models.todo(user, argument)

    elif args[0] == 'watch' and args[1] != None:
        args[1] = args[1].strip()
        filterstr = Config.get_filter(args[1])
        if filterstr == None:
            if 'jira.n.xiaomi.com/browse' in args[1]:
                user.startWatch(args[1])
            elif ' ' not in args[1] and '/' not in args[1]:
                user.startWatch(f'http://jira.n.xiaomi.com/browse/{args[1]}')
            elif ' ' in args[1]:
                filterstr = args[1]
        
        if filterstr != None:
            for link in user.getJiraLinks(filterstr, 'all'):
                user.startWatch(link)
        else:
            print('expect for a valid filter expression')


    elif args[0] == 'dispatch' and args[1] != None:
        args[1] = args[1].strip()
        filterstr = Config.get_filter(args[1])
        if filterstr == None:
            if 'jira.n.xiaomi.com/browse' in args[1]:
                user.dispatch(args[1])
            elif ' ' not in args[1] and '/' not in args[1]:
                user.dispatch(f'http://jira.n.xiaomi.com/browse/{args[1]}')
            elif ' ' in args[1]:
                filterstr = args[1]
        
        if filterstr != None:
            for link in user.getJiraLinks(filterstr, 'all'):
                user.dispatch(link)
        else:
            print('expect for a valid filter expression')


    elif args[0] == 'random' and args[1] != None:
        import random
        owners = ['hujinqi', 'weijuncheng']
        endint = len(owners) - 1
        
        args[1] = args[1].strip()
        filterstr = Config.get_filter(args[1])
        if filterstr == None:
            if 'jira.n.xiaomi.com/browse' in args[1]:
                owner = owners[random.randint(0, endint)]
                user.dispatch_owner(args[1], owner)
            elif ' ' not in args[1] and '/' not in args[1]:
                owner = owners[random.randint(0, endint)]
                user.dispatch_owner(f'http://jira.n.xiaomi.com/browse/{args[1]}', owner)
            elif ' ' in args[1]:
                filterstr = args[1]
        
        if filterstr != None:
            for link in user.getJiraLinks(filterstr, 'all'):
                owner = owners[random.randint(0, endint)]
                user.dispatch_owner(link, owner)
        else:
            print('expect for a valid filter expression')

    else:
        print('invalid params')
        exit(1)


if __name__ == '__main__':
    main()
    