import os
import requests
import re
import json


path = '%s/config/models.json'%os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def touch_models_table(user):
    uri = 'http://husky.pt.miui.com/device/info'
    resp = user.session.get(uri)
    if response.url != uri:
            printer.auth_error()
            exit(0)
    html = resp.text

    models_pattern = re.compile(r'<tr>.*?</tr>', re.S)
    model_descs = models_pattern.findall(html)
    model_descs = model_descs[1:]

    details_pattern = re.compile(r'<td.*?>(.*?)</td>')
    models = list()

    for model in model_descs:
        details = details_pattern.findall(model)
        if len(details) == 8:
            model = {}
            model['name'] = details[0]
            model['model'] = details[1]
            if model not in models:
                models.append(model)

    with open(path, 'w') as f:
        json.dump(models, f, ensure_ascii=False, indent=4)
    


def find_target_model(user, key):
    if not os.path.exists(path):
        print('input cmd： components whats init')
        exit(0)
    
    with open(path, 'r') as f:
        models = json.load(f)
    
    outputs = list()
    max_l = 0
    key = key.replace('手机', '').lower()
    for model in models:
        if key in model['name'].replace('手机','').lower() or key in model['model'].lower():
            extra = 0
            if '手机' not in model['name']:
                extra = 2
            output = f"*{' '*4}{model['name'].ljust(30+extra)}{model['model'].ljust(10)}{' '*4}"
            if len(output) > max_l:
                max_l = len(output)
            outputs.append(output)

    
    print('')
    if len(outputs) == 0:
        print("* can't find the mobile info".ljust(41))
    else:
        for output in outputs:
            print(output)
    print('')


def todo(user, key):
    if key == 'init':
        touch_models_table(user)
    else:
        find_target_model(user, key)
