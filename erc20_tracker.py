from web3 import Web3, HTTPProvider
import json
import requests
import time
import os
from tools import send_email, send_text, load_json, get_abi

class User():
    def __init__(self, email = '', phone = ''):
        self.notify = True
        self.tracked_coins = 'all'
        self.tracked_from_addresses = 'all'
        self.tracked_to_addresses = 'all'
        self.email = email
        self.phone = phone
        self.notify = True if self.email or self.phone

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

class Coin():
    def __init__(self, name, address, abi, external):
        print('Initializing {}'.format(name))
        self.name = name
        self.address = address
        self.w3 = external['web3']
        self.uni = external['uni']
        self.abi = abi

        if self.abi:
            self.contract = self.w3.eth.contract(address=self.address, abi=self.abi)
            self.supply = self.contract.functions.totalSupply().call()
            self.decimals = self.contract.functions.decimals().call()
            self.liquidity = self.get_liquidity()


    def get_liquidity(self):
        liquidity = self.get_uniswap_liquidity(0.1)
        return liquidity

    def get_uniswap_liquidity(self, slippage):
        exchange_address = uni.factory_contract.functions.getExchange(self.address).call()
        token_reserve = self.contract.functions.balanceOf(exchange_address).call()
        #eth_reserve = self.w3.eth.getBalance(exchange_address)

        # sell_token_no_slippage = volume * eth_reserve/token_reserve
        # sell_token_slippage = volume * eth_reserve/(token_reserve + sell_amount)
        #
        # slippage = 1 - sell_token_slippage/sell_token_no_slippage #Solve for volume

        volume = slippage/(1-slippage)*token_reserve
        return volume

class Worker():
    def __init__(self, external, coins, users):
        self.w3 = external['web3']
        self.external = external
        self.coins = coin_list
        self.notify = True
        self.users = users

    def check_large_tx(self, block):
        print('{} -- {} Txs'.format(block.number, len(block.transactions)))
        for coin in self.coins:
            for tx in block.transactions:
                if tx.to == coin.address:
                    inputs = coin.contract.decode_function_input(tx.input)
                    if inputs[0].fn_name == 'transfer':
                        print('--------------')
                        print(coin.name)
                        print(inputs)
                        volume = 0 # inputs[1].get('_value',inputs[1].get('_amount',0))
                        if '_value' in inputs[1].keys():
                            volume = inputs[1]['_value']
                        elif '_amount' in inputs[1].keys():
                            volume = inputs[1]['_amount']

                        if volume> coin.liquidity:
                            fraction = volume/coin.liquidity
                            if volume > coin.liquidity:
                                print('Large tx')
                                print(coin.name, fraction)
                                for user in self.users:
                                    if user.notify:
                                        self.send_notifications(tx, user, coin, fraction)

    def send_notifications(self, tx, coin, fraction):
            body = self.body(tx, coin, fraction)
            for user in users:
                if user.email:
                    send_email(user.email, subject, body)
                if user.phone:
                    send_text(user.email, subject, body)

    def make_body(self, tx, coin, fraction):
        body = '{} percent of the total supply of {} was sent on chain. \n\n Tx hash: {}'.format(fraction*100, coin, tx.hash)
        return body

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


def make_coin_objects(external):
    coin_info = load_json('coin_info.json')
    coins = []
    for coin in coin_info.keys():
        #Fetch the abi if key isn't prevent in file
        #Allows for adding coins without looking for abi
        coin_info[coin]['abi'] = coin_info[coin].get('abi', get_abi(coin['address']))
        coins.append(Coin(info['address'], coin_info[coin]['abi'], external))

    with open('coin_info.json',w) as f:
        json.dump(coin_info, f)

    return coins





# PROVIDER = "wss://mainnet.infura.io/ws/v3/314056fe262245dc8b549c48778b176b"
# w3 = Web3(Web3.WebsocketProvider(PROVIDER, websocket_kwargs = {websocket_timeout = 50}))

# w3 = Web3(HTTPProvider("https://mainnet.infura.io/v3/314056fe262245dc8b549c48778b176b"))
uni = Uniswap(w3)
external = {'uni':uni, 'web3': w3}




coin_list = make_coin_objects(external)
#work = Worker(external, coin_list)
