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
    import os
    import getpass
    import shutil
    # /home/hujinqi/.config/google-chrome/Default
    path = f'/home/{getpass.getuser()}/.config/google-chrome/Default/Cookies'
    shutil.copy(path, os.path.dirname(os.path.abspath(__file__)))

    conn = sqlite3.connect(f'{os.path.dirname(os.path.abspath(__file__))}/Cookies')
    cursor = conn.cursor()
    cursor = conn.execute("select name, encrypted_value from cookies where host_key = 'cas.mioffice.cn'")

    cookie = "" 
    for row in cursor:
        ENCRYPTED_VALUE = row[1]
        cookie += row[0] + "=" + decrypt(MY_PASS, ENCRYPTED_VALUE) +"; "
    conn.close()

    os.remove(f"{os.path.dirname(os.path.abspath(__file__))}/Cookies")
    return cookie[0:-2]
