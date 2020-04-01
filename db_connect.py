import sqlite3



class connect():
    def __init__(self, db_name='transactions.db', rows = None):
        self.file = db_name
        self.rows = rows
    def __enter__(self):
        self.conn = sqlite3.connect(self.file)
        if self.rows == 'as_dict':
            self.conn.row_factory = dict_factory
        elif self.rows == 'first_val':
            self.conn.row_factory = lambda cursor, row: row[0]
        return self.conn.cursor()
    def __exit__(self, type, value, traceback):
        self.conn.commit()
        self.conn.close()
#
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# Table:
#
# with connect('transactions.db') as c:
#     c.execute("""DROP TABLE uniswap""")
#     c.execute("""CREATE TABLE uniswap (block_number INTEGER, token TEXT,
#         token_reserve TEXT, eth_reserve TEXT, price TEXT, UNIQUE(block_number, token))""")
#
# with connect('transactions.db') as c:
#     c.execute("""DROP TABLE ether""")
#     c.execute("""CREATE TABLE ETH (block_number INTEGER, tx_hash TEXT UNIQUE,
#         from_address TEXT, to_address TEXT, value TEXT, input TEXT, timestamp INTEGER,
#         gas INTEGER, gas_price INTEGER, nonce INTEGER, r TEXT, s TEXT, v INTEGER)""")
#
# for coin in coins:
#     with connect('transactions.db') as c:
#         c.execute("""DROP TABLE {}""".format(coin.name))
#         c.execute("""CREATE TABLE {} (block_number INTEGER, tx_hash TEXT UNIQUE,
#             from_address TEXT, to_address TEXT, value TEXT, timestamp TEXT)""".format(coin.name))


# with connect('transactions.db') as c:
#     #c.execute("""DROP TABLE ETH""")
#     c.execute("""CREATE TABLE BAT (block_number INTEGER, tx_hash TEXT UNIQUE,
#         from_address TEXT, to_address TEXT, value TEXT, timestamp TEXT)""")
