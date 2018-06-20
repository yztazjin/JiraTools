from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2


# Function to get rid of padding
def decrypt(my_pass, encrypted_value):

    def clean(x): 
        return x[:-x[-1]].decode('utf8')

    # Trim off the 'v10' that Chrome/ium prepends
    encrypted_value = encrypted_value[3:]

    # Default values used by both Chrome and Chromium in OSX and Linux
    salt = b'saltysalt'
    iv = b' ' * 16
    length = 16

    # On Mac, replace MY_PASS with your password from Keychain
    # On Linux, replace MY_PASS with 'peanuts'
    # my_pass = MY_PASS
    # my_pass = my_pass.encode('utf8')

    # 1003 on Mac, 1 on Linux
    iterations = 1

    key = PBKDF2(my_pass, salt, length, iterations)
    cipher = AES.new(key, AES.MODE_CBC, IV=iv)

    decrypted = cipher.decrypt(encrypted_value)
    return clean(decrypted)


def chrome_cookie():
    
    # assert valid cookie
    assert_cookie()

    import secretstorage

    bus = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(bus)
    MY_PASS = 'peanuts'.encode('utf8')
    for item in collection.get_all_items():
        if item.get_label() == 'Chrome Safe Storage':
            MY_PASS = item.get_secret()
            break
    else:
        print('Chrome password not found!')

    import sqlite3
    import getpass
    # /home/hujinqi/.config/google-chrome/Default
    path = f'/home/{getpass.getuser()}/.config/google-chrome/Default/Cookies'
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("select name, encrypted_value from cookies where host_key = 'cas.mioffice.cn'")
    datas = cursor.fetchall()
    conn.close()

    cookie = "" 
    for row in datas:
        if row[0] == 'CASTGC':
            continue
        ENCRYPTED_VALUE = row[1]
        cookie += row[0] + "=" + decrypt(MY_PASS, ENCRYPTED_VALUE) +"; "

    return cookie[0:-2]


# just a format printer
import asyncio
import sys
import itertools

@asyncio.coroutine
def wait_printer():   
    print('')
    write, flush = sys.stdout.write, sys.stdout.flush
    for dot in itertools.cycle([".  ", ".. ", "..."]):
        line = 'wait chrome update chookies '+dot
        write(line)
        flush()
        write('\x08' * len(line))
        try:
            yield from asyncio.sleep(.6)
        except asyncio.CancelledError:
            write(' ' * len(line) + '\x08' * len(line))
            write('chrome has updated the cookies db\n')
            flush()
            break


@asyncio.coroutine
def doAssert():
    spinner = asyncio.async(wait_printer())
    result = yield from check_chrome_autoupdate()
    spinner.cancel()
    return result


@asyncio.coroutine
def check_chrome_autoupdate():
    import os,sys
    
    try:
        from JiraTools.config import Config
    except Exception:
        pwd = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.dirname(pwd))
        from JiraTools.config import Config

    config_flag_value = Config.load_config()['cookie_update_flag']
    
    if config_flag_value == 0:
        return True

    import sqlite3
    import getpass
    # /home/hujinqi/.config/google-chrome/Default
    path = f'/home/{getpass.getuser()}/.config/google-chrome/Default/Cookies'
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    result = False
    max_time = 0
    while True and max_time < 60:

        cursor.execute("select last_access_utc from cookies where host_key = 'cas.mioffice.cn' and name = 'TGC'")
        datas = cursor.fetchall()
    
        flag_value = -100
        if len(datas) > 0:
            flag_value = datas[0][0]
        elif config_flag_value != -100:
            result = False
            break

        if flag_value != config_flag_value:
            config = Config.load_config()
            config['cookie_update_flag'] = 0
            Config.dump_config(config)
            result = True
            break
        else:
            yield from asyncio.sleep(5)
            max_time += 5
    
    conn.close()
    return result


def assert_cookie():
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(doAssert())
    loop.close()

    if not result:
        print('make sure you have refresh the https://cas.mioffice.cn/login on chrome')
        exit(0)
