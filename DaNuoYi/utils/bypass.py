# -*- coding: utf-8 -*-
# file: bypass.py
# time: 2021/7/29
# author: yangheng <yangheng@m.scnu.edu.cn>
# github: https://github.com/yangheng95
# Copyright (C) 2021. All Rights Reserved.

# -*- coding: utf-8 -*-
# file: bypass.py
# time: 2021/7/29
# author: yangheng <yangheng@m.scnu.edu.cn>
# github: https://github.com/yangheng95
# Copyright (C) 2021. All Rights Reserved.

import random

import requests

import libinjection

from DaNuoYi.evolution.entity.individual import Individual
from DaNuoYi.global_config import NGX_LUA_WAF, MODSECURITY_WAF, TIMEOUT


def construct_user_input(payload):
    payload = payload.replace(' ', '')
    payload = payload.replace('[blank]', ' ')
    payload = payload.replace('[terDigitExcludingZero]', str(random.randint(1, 10)))
    return payload


def is_bypass(individual: Individual, waf_address, return_code=False):

    try:
        session = requests.session()
        session.keep_alive = False

        task = individual.task
        individual = individual.injection

        payload = construct_user_input(individual)

        

        if '5000' in waf_address:
            waf_address = "http://www.itsecgames.com/"
            if task == 'sqli':
                response = libinjection.is_sql_injection(f"http://testphp.vulnweb.com/main.php?SmallClass={payload}")
                if response['is_sqli'] == True:
                    return (True, 200) if return_code else True
                return (False, 404) if return_code else False
            elif task == 'xss':
                response = libinjection.is_xss(f"http://testphp.vulnweb.com/index.php?name={payload}")
                if response['is_xss'] == True:
                    return (True, 200) if return_code else True
                return (False, 404) if return_code else False
            elif task == 'phpi':
                response = libinjection.is_sql_injection(f"http://testphp.vulnweb.com/main.php?SmallClass={payload}")
                if response['is_sqli'] == True:
                    return (True, 200) if return_code else True
                return (False, 404) if return_code else False
            elif task == 'osi':
                response = libinjection.is_sql_injection(f"http://testphp.vulnweb.com/main.php?SmallClass={payload}")
                if response['is_sqli'] == True:
                    return (True, 200) if return_code else True
                return (False, 404) if return_code else False
            elif task == 'xmli':
                response = libinjection.is_sql_injection(f"http://testphp.vulnweb.com/main.php?SmallClass={payload}")
                if response['is_sqli'] == True:
                    return (True, 200) if return_code else True
                return (False, 404) if return_code else False
            elif task == 'htmli':
                response = libinjection.is_sql_injection(f"http://testphp.vulnweb.com/main.php?SmallClass={payload}")
                if response['is_sqli'] == True:
                    return (True, 200) if return_code else True
                return (False, 404) if return_code else False
            else:
                raise KeyError('Unknown injection type!')
        elif '8888' in waf_address:
            url_get = waf_address
            params = {"title": payload, "action": "search"}
            response = session.get(url=url_get, params=params, timeout=TIMEOUT)
        elif '7777' in waf_address:
            url_get = waf_address
            params = {"title": payload, "action": "search"}
            try:
                response = session.get(url=url_get, params=params, timeout=TIMEOUT)
            except Exception as e:
                print('Exception in bypass checking: {}'.format(e))
                return False, 800 if return_code else False
        else:
            raise KeyError('Unrecognized WAF address: {}!'.format(waf_address))

        # if response['is_sql'] == True:
        #     return (True, 200) if return_code else True
        # return (False, 404) if return_code else False

    except Exception as e:
        return is_bypass(individual, waf_address, return_code)

