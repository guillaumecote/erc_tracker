from web3 import Web3, HTTPProvider
import json
import requests
import time
import dill
import os
import smtplib
import ssl


def send_email(recipient, subject, body):
    with open('email_creds.json') as f:
        creds = json.load(f)
    gmail_user, gmail_pwd = creds['email'], creds['password']

    FROM = gmail_user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print('Successfully sent the mail')
    except Exception as e:
        print(e)
        print("Failed to send mail")

emaillist=[""]

class Uniswap():
    def __init__(self, w3):
        self.abi = self.load_abi()
        self.factory_contract = w3.eth.contract(address="0xc0a47dFe034B400B47bDaD5FecDa2621de6c4d95", abi = self.abi['factory'])

    def load_abi(self):
        abi = {}
        with open('uniswap_exchange.json') as f:
            abi['exchange'] = json.load(f)

        with open('uniswap_factory.json') as f:
            abi['factory'] = json.load(f)
        return abi
# class DEXes():
#     __init__(self):
#

#dexes = {'uni': Uniswap()}

class Coin():
    def __init__(self, name, address, external, abi = None):
        print('Initializing {}'.format(name))
        self.name = name
        self.address = address
        self.w3 = external['web3']
        self.uni = external['uni']
        if abi:
            self.abi = abi
        else:
            self.abi = self.get_abi()

        if self.abi:
            self.contract = self.w3.eth.contract(address=self.address, abi=self.abi)
            self.supply = self.contract.functions.totalSupply().call()
            self.decimals = self.contract.functions.decimals().call()
            self.liquidity = self.get_liquidity()

    def get_abi(self):
        resp = requests.get('https://api.etherscan.io/api?module=contract&action=getabi&address='+self.address).json()
        if resp['status'] == '1':
            return resp['result']
        else:
            print('Error while loading abi for {}'.format(self.name))
            print(resp['message'])
            return []

    def get_liquidity(self):
        liquidity = self.get_uniswap_liquidity(0.1)
        return liquidity

    def get_uniswap_liquidity(self, slippage):
        exchange_address = uni.factory_contract.functions.getExchange(self.address).call()
        token_reserve = self.contract.functions.balanceOf(exchange_address).call()
        #eth_reserve = self.w3.eth.getBalance(exchange_address)


        #
        # sell_token_no_slippage = volume * eth_reserve/token_reserve
        # sell_token_slippage = volume * eth_reserve/(token_reserve + sell_amount)
        #
        # slippage = 1 - sell_token_slippage/sell_token_no_slippage #Solve for volume

        volume = slippage/(1-slippage)*token_reserve
        return volume

class Worker():
    def __init__(self, external, coin_obj_list):
        self.w3 = external['web3']
        self.external = external
        self.coin_obj_list = coin_list
        #self.make_coin_objects()

    def check_large_tx(self, block):
        print('{} -- {} Txs'.format(block.number, len(block.transactions)))
        for coin in self.coin_obj_list:
            for tx in block.transactions:
                if tx.to == coin.address:
                    inputs = coin.contract.decode_function_input(tx.input)
                    if inputs[0].fn_name == 'transfer':
                        print('--------------')
                        print(coin.name)
                        print(inputs)
                        if '_value' in inputs[1].keys():
                            print(inputs[1]['_value']/coin.supply*100)
                            if inputs[1]['_value'] > coin.liquidity:
                                print('LARGE TX')
                        if '_amount' in inputs[1].keys():
                            print(inputs[1]['_amount']/coin.supply*100)
                            if inputs[1]['_value'] > coin.liquidity:
                                print('LARGE TX')

    def send_notification(self, tx, coin, fraction):
        if self.notify:
            send_email(recipient, subject, body)

    def make_body(self, tx, coin, fraction):
        body = 'A large {} transaction was sent of '.format(coin, tx.hash)

    def run_continuously(self, from_block = None):
        if from_block:
            previous_block_num = from_block
        else:
            previous_block_num = 100000000
        while True:
            block = self.w3.eth.getBlock('latest',full_transactions = True)
            missed_blocks = []
            for i in range(previous_block_num + 1, block.number):
                missed_blocks.append(self.w3.eth.getBlock(i,full_transactions = True))
                time.sleep(0.5)
            missed_blocks.append(block)
            for block in missed_blocks:
                self.check_large_tx(block)

            previous_block_num = block.number
            time.sleep(20)
            print('LAST BLOCK NUM -- {}'.format(previous_block_num))


def make_coin_objects():
    fname = 'coin_obj.dill'
    coin_addresses = load_coin_addresses()
    # if os.path.isfile(fname):
    #     with open(fname, 'rb') as f:
    #         self.coin_obj_list = dill.load(f)
    coin_obj_list = []
    for name, address in coin_addresses.items():
        if name not in (c.name for c in coin_obj_list):
            coin_obj_list.append(Coin(name, address, external))
            time.sleep(4)
    return coin_obj_list
    # with open(fname, 'wb') as f:
    #     dill.dump(self.coin_obj_list, f)


def load_coin_addresses():
    fname = 'coin_addresses.json'
    if os.path.isfile(fname):
        with open(fname) as f:
            addresses = json.load(f)
        return addresses
    else:
        return {}



# PROVIDER = "wss://mainnet.infura.io/ws/v3/314056fe262245dc8b549c48778b176b"
# w3 = Web3(Web3.WebsocketProvider(PROVIDER))

w3 = Web3(HTTPProvider("https://mainnet.infura.io/v3/314056fe262245dc8b549c48778b176b"))
uni = Uniswap(w3)
external = {'uni':uni, 'web3': w3}




coin_list = make_coin_objects()
work = Worker(external, coin_list)
