from db_connect import connect
import itertools as it
import sqlite3
import os
import json
from erc20_tracker import *
from tools import *
import numpy as np
import traceback

class Historical():
    TX_LOAD_LIMIT = 100000
    TX_FETCH_LIMIT = 100
    EARLIEST_BLOCK = 7000000

    def __init__(self, coins):

        self.coins = coins

        self.w3 = load_web3()
        with open('../creds/etherscan_creds.json') as f:
            self.etherscan_API_KEY =  json.load(f)['API_KEY']

        with open('uniswap_factory.json') as f:
            factory_abi = json.load(f)
        self.uni_factory_contract = self.w3.eth.contract(address="0xc0a47dFe034B400B47bDaD5FecDa2621de6c4d95", abi = factory_abi)

    def get_known_block_nums(self, table, block_range = 'all'):
        if block_range == 'all':
            with connect(rows = 'first_val') as c:
                fetched_blocks = c.execute('SELECT DISTINCT block_number FROM {}'.format(table)).fetchall()
        elif len(block_range) == 2 and block_range[1] >= block_range[0]:
            with connect(rows = 'first_val') as c:
                fetched_blocks = c.execute("SELECT DISTINCT block_number FROM {} WHERE block_number >= ? AND block_number <= block_number ORDER BY block_number DESC LIMIT ?",
                (block_range[0], block_range[1])).fetchall()
        return fetched_blocks

    def missing_blocks_in_range(self, block_range):
        known_blocks = self.get_known_block_nums(block_range)
        missing_blocks = [i for i in range(block_range[0], block_range[1]) if i not in known_blocks]
        return missing_blocks

    def web3_fetch_blocks(self, block_range):
        with connect(rows = 'first_val') as c:
            fetched_blocks = c.execute('SELECT DISTINCT block_number FROM ether').fetchall()

        missing_blocks = (block_num for block_num in range(block_range[0], block_range[1]) if block_num not in fetched_blocks)
        for block_num in missing_blocks:
            try:
                print('Fetching block number {}'.format(block_num))
                block = self.w3.eth.getBlock(block_num,full_transactions = True)
                inserted_tx = save_block_txs(block, self.coins)
                if not inserted_tx:
                    with connect() as c:
                        c.execute("INSERT INTO transactions(block_number) VALUES(?)",(str(block_num)))
            except Exception as e:
                print('Error with block {}'.format(block_num))
                print(traceback.format_exc())
                return False
        return True

    def load_blocks(self, block_range = 'all'):
        if block_range == 'all':
            with connect(rows = 'as_dict') as c:
                saved_transactions = c.execute('SELECT * FROM ether ORDER BY block_number DESC LIMIT ?', (self.TX_LOAD_LIMIT,)).fetchall()
        elif len(block_range) == 2 and block_range[1] >= block_range[0]:
            with connect(rows = 'as_dict') as c:
                saved_transactions = c.execute("SELECT * FROM ether WHERE block_number >= ? AND block_number <= ? ORDER BY block_number DESC LIMIT ?",
                (block_range[0], block_range[1], self.TX_LOAD_LIMIT)).fetchall()
        return [Transaction(tx) for tx in saved_transactions if tx['tx_hash']]

    def get_current_uniswap_state(self, coin):
        print(coin)
        print(coin.name, coin.address)
        block_number = self.w3.eth.blockNumber
        exchange_address = self.uni_factory_contract.functions.getExchange(coin.address).call(block_identifier=block_number)
        token_reserve = coin.contract.functions.balanceOf(exchange_address).call(block_identifier=block_number)
        eth_reserve = self.w3.eth.getBalance(exchange_address, block_identifier=block_number)
        price = (eth_reserve/10**18)/(token_reserve/10**coin.decimals)
        with connect() as c:
            c.execute("INSERT INTO uniswap VALUES(?, ?, ?, ?, ?)", (block_number, coin.name, str(token_reserve), str(eth_reserve), str(price)))
        print('Successfully got state for {}'.format(coin.name))
        print(block_number, coin.name, str(token_reserve), str(eth_reserve), str(price))
        return {'block_number':block_number, 'token':coin.name, 'token_reserve': token_reserve, 'eth_reserve': eth_reserve, 'price': price}

    def save_state(self, state):
        # with connect() as c:
        #     c.execute("INSERT INTO uniswap VALUES(?, ?, ?, ?, ?)", (block_number, coin.name, str(token_reserve), str(eth_reserve), str(price)))
        print(state)

    def get_known_uniswap_state(self, coin, block_num):
        with connect(rows = 'as_dict') as c:
            rows = c.execute('SELECT * from uniswap WHERE block_number = {} and token LIKE "{}"'.format(block_num, coin.name)).fetchall()
        return rows


    def calculate_uniswap_state(self, coin, block_num): # This is O(infinity) and ugly, will come back to it later
        with connect(rows = 'first_val') as c:
            fetched_blocks = c.execute('SELECT DISTINCT block_number FROM uniswap').fetchall()
        if block_num in fetched_blocks:
            state = self.get_known_uniswap_state(coin, block_num)
            print('Returning already stored Uniswap state for block {}'.format(block_num))
            return state
        else:
            state = self.get_current_uniswap_state(coin)
            with connect(rows = 'first_val') as c:
                amounts_in = c.execute('SELECT value FROM {} WHERE to_address LIKE "{}" AND block_number > {}'.format(coin.name, coin.uni_exchange_address, block_num)).fetchall()
                amounts_out = c.execute('SELECT value FROM {} WHERE from_address LIKE "{}" AND block_number > {}'.format(coin.name, coin.uni_exchange_address, block_num)).fetchall()

            sum_amounts_in = sum((float(a) for a in amounts_in))
            sum_amounts_out = sum((float(a) for a in amounts_out))
            token_reserve = float(state['token_reserve']) - sum_amounts_in + sum_amounts_out

            with connect(rows = 'first_val') as c:
                amounts_in = c.execute('SELECT value FROM ETH WHERE to_address LIKE "{}" AND block_number > {}'.format(coin.uni_exchange_address, block_num)).fetchall()
                amounts_out = c.execute('SELECT value FROM ETH WHERE from_address LIKE "{}" AND block_number > {}'.format(coin.uni_exchange_address, block_num)).fetchall()

            sum_amounts_in = sum((float(a) for a in amounts_in))
            sum_amounts_out = sum((float(a) for a in amounts_out))
            eth_reserve = float(state['eth_reserve']) - sum_amounts_in + sum_amounts_out
            price = (eth_reserve/10**18)/(token_reserve/10**coin.decimals)

            with connect() as c:
                c.execute("INSERT INTO uniswap VALUES(?, ?, ?, ?, ?)", (block_num, coin.name, str(token_reserve), str(eth_reserve), str(price)))
            print('Successfully got state for {}'.format(coin.name))
            print(block_num, coin.name, str(token_reserve), str(eth_reserve), str(price))
            return {'block_number':block_num, 'token':coin.name, 'token_reserve': token_reserve, 'eth_reserve': eth_reserve, 'price': price}


        # else:
        #     nearest_known_block = next((f for f in reversed(fetched_blocks) if f>block_num), None)
        #     if nearest_known_block:
        #         block_range = [block_num, nearest_known_block - 1]
    #             missing_blocks = self.missing_blocks_in_range(block_range)
    #             if len(missing_blocks) <= self.TX_FETCH_LIMIT:
    #                 fully_fetched = self.web3_fetch_blocks(block_range)
    #                 if fully_fetched:
    #                     state = self.get_known_uniswap_state(self, nearest_known_block)
    #                     transactions = self.load_blocks(block_range) # Maybe add tx filters to the request
    #                     for coin in coins:
    #                         eth_reserve = [s['eth_reserve'] for s in state if s['token'] == coin.name]
    #                         token_reserve = [s['eth_reserve'] for s in state if s['token'] == coin.name]
    #                         current_block = nearest_known_block - 1
    #                         for tx in transactions:
    #                             if tx.block_number != current_block:
    #                                 price = (eth_reserve/10**18)/(token_reserve/10**coin.decimals)
    #                                 self.save_state(current_block, coin.name, token_reserve, eth_reserve, price)
    #                                 current_block = tx.block_number
    #                             current_block = tx.block_number
    #                             if tx.from_address == coin.uni_exchange_address:
    #                                 eth_reserve -= tx.value
    #                                 token_reserve -=
    #
    #
    #                     tx_by_block = {}
    #                     for tx in transactions:
    #                         tx_by_block[tx.block_number] = tx
    #                     uni_state = {}
    #                     for coin in coins:
    #                         uni_state[coin.name]
    #                          for tx in transactions:
    #
    #
    #                     for coin in self.coins:
    #
    #             else:
    #                 print("Uniswap state calculation requires {} web3 calls, which is more than the current set limit of {}".format(len(missing_blocks) self.TX_FETCH_LIMIT))
    #                 return None
    #         else:
    #             print("Uniswap state at block {} can't be calculated with current fetched data. Most recent fetched block is {}".format(block_num, fetched_blocks[0]))
    #             return None
    #
    #   if min(fetched_blocks, key=lambda x:abs(x-block_number))
    #       pass

    def get_erc20_transactions(self, coin, block_range = 'all'):
        try:
            if block_range == 'all':
                startblock=7000000
                endblock=999999999999
            else:
                startblock=block_range[0]
                endblock=block_range[1]

            params = {'module':'account',
                        'action':'tokentx',
                        'contractaddress': coin.address,
                        'startblock': startblock,
                        'endblock': endblock,
                        'sort':'desc',
                        'apikey': self.etherscan_API_KEY}
            etherscan_query_loop(coin.name, params)

        except Exception as e:
            print(traceback.format_exc())

    def get_eth_txs_to_uniswap(self, coin, block_range = 'all'):
        #get regular txs for address
        if block_range == 'all':
            startblock=7000000
            endblock=999999999999
        else:
            startblock=block_range[0]
            endblock=block_range[1]

        params = {'module':'account',
                    'action':'txlist',
                    'address': coin.uni_exchange_address,
                    'startblock': startblock,
                    'endblock': endblock,
                    'sort':'desc',
                    'apikey': self.etherscan_API_KEY}
        etherscan_query_loop('ETH', params)
        params['action'] = 'txlistinternal'
        params['endblock'] = endblock
        etherscan_query_loop('ETH', params)


class Transaction():
    def __init__(self, transaction_dict):
        self.transaction_dict = transaction_dict
        for k, v in transaction_dict.items():
            setattr(self, k, v)

    def __iter__(self):
        return (key for key in self.transaction_dict.keys())

w3 = load_web3()
uni = Uniswap(w3)
coins = make_coin_objects(w3, uni)
load = Loader(coins)
