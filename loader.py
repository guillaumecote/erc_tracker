from db_connect import connect
import itertools as it
import sqlite3
import os
import json
from erc20_tracker import make_coin_objects

class Loader():
    TX_LOAD_LIMIT = 100000

    def __init__(self, w3, coins):
        self.w3 = w3
        self.coins = coins

    def load_coin_addresses(self):
        fname = 'coin_addresses.json'
        if os.path.isfile(fname):
            with open(fname) as f:
                addresses = json.load(f)
            return addresses
        else:
            return {}


    def fetch_blocks(self, block_range):
        with connect(rows = 'first_val') as c:
            fetched_blocks = c.execute('SELECT DISTINCT block_number FROM transactions').fetchall()

        missing_blocks = (block_num for block_num in range(block_range[0], block_range[1]) if block_num not in fetched_blocks)
        for block_num in missing_blocks:
            print('Fetching block number {}'.format(block_num))
            block = self.w3.eth.getBlock(block_num,full_transactions = True)
            save_block_txs(block, self.coins)

    def load_blocks(self, block_range = 'all'):
        if block_range == 'all':
            with connect() as c:
                saved_transactions = c.execute('SELECT * FROM transactions ORDER BY block_number DESC LIMIT ?', (self.TX_LOAD_LIMIT,)).fetchall()
        elif len(block_range) == 2 and block_range[1] >= block_range[0]:
            with connect() as c:
                saved_transactions = c.execute("SELECT * FROM transactions WHERE block_number >= ? AND block_number <= block_number ORDER BY block_number DESC LIMIT ?",
                (block_range[0], block_range[1], self.TX_LOAD_LIMIT)).fetchall()
        return [Transaction(tx) for tx in saved_transactions]

    def get_current_uniswap_state(self):
        abi = {}
        with open('uniswap_exchange.json') as f:
            abi['exchange'] = json.load(f)

        with open('uniswap_factory.json') as f:
            abi['factory'] = json.load(f)
        factory_contract = self.w3.eth.contract(address="0xc0a47dFe034B400B47bDaD5FecDa2621de6c4d95", abi = abi['factory'])

        block_number = self.w3.eth.blockNumber

        with connect() as c:
            for coin self.coins:
                exchange_address = factory_contract.functions.getExchange(coin.address).call(block_identifier=block_number)
                token_reserve = coin.contract.functions.balanceOf(exchange_address).call(block_identifier=block_number)
                eth_reserve = self.w3.eth.getBalance(exchange_address, block_identifier=block_number)
                price = (eth_reserve/10**18)/(token_reserve/10**coin.decimals)
                c.execute("INSERT INTO transactions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(block.number, tx.hash.hex(), tx['from'], tx.to, str(tx.value), tx.input,
                int(block.timestamp), tx.gas, tx.gasPrice, tx.nonce, tx.r.hex(), tx.s.hex(), tx.v))


class Transaction():
    def __init__(self, transaction_dict):
         for k, v in transaction_dict.items():
             setattr(self, k, v)


coins = make_coin_objects()
