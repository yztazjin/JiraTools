import os, sys
try:
    from JiraTools.config import Config
except Exception as e:
    pwd = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.dirname(pwd))
    from JiraTools.config import Config

#Cookie失效更新标记，直到Cookie更新成功，移除标记
def auth_error():
    print('chrome browser >>> https://cas.mioffice.cn/login to refresh chrome-cookie')

    import sqlite3
    import getpass
    # /home/username/.config/google-chrome/Default
    path = f'/home/{getpass.getuser()}/.config/google-chrome/Default/Cookies'
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("select last_access_utc from cookies where host_key = 'cas.mioffice.cn' and name = 'TGC'")
    datas = cursor.fetchall()
    conn.close()
    
    print(datas)
    flag_value = -100
    if len(datas) > 0:
        flag_value = datas[0][0]
    
    config = Config.load_config()
    config['cookie_update_flag'] = flag_value
    Config.dump_config(config)