import requests
import os
import json
import smtplib
import ssl
from twilio.rest import TwilioRestClient
from web3 import Web3, HTTPProvider, WebsocketProvider
from urllib.parse import urlencode
from ratelimit import limits, sleep_and_retry
from db_connect import connect
import traceback

def send_text(body):
    with open('../creds/twilio_creds.json') as f:
        creds = json.load(f)
    client = TwilioRestClient(creds['account_sid'], creds['auth_token'])
    client.messages.create(to="+18192308597", from_=creds['phone_from'], body=body)

def send_email(recipient, subject, body):
    with open('../creds/smtp_creds.json') as f:
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

def load_web3(provider = 'HTTP'):
    with open('../creds/infura_creds.json') as f:
        creds = json.load(f)

    if provider == 'HTTP':
        w3 = Web3(HTTPProvider(creds[provider]))
    elif provider == 'WSS':
        w3 = Web3(WebsocketProvider(creds[provider], websocket_kwargs = {websocket_timeout : 50}))
    else:
        raise ValueError('Provider should be HTTP or WSS, received {} instead'.format(provider))
    return w3

def get_abi(address):
    resp = requests.get('https://api.etherscan.io/api?module=contract&action=getabi&address='+address).json()
    if resp['status'] == '1':
        return resp['result']
    else:
        print('Error while loading abi for {}'.format(address))
        print(resp['message'])
        return []

def load_json(fname):
    if os.path.isfile(fname):
        with open(fname) as f:
            json_data = json.load(f)
        return json_data
    else:
        return {}

def save_block_txs(block, coins):
    inserted_tx = False
    with connect() as c:
        for tx in block.transactions:
            if tx.to in (c.address for c in coins):
                try:
                    c.execute("INSERT INTO ether VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(block.number, tx.hash.hex(), tx['from'], tx.to, str(tx.value), tx.input,
                    int(block.timestamp), tx.gas, tx.gasPrice, tx.nonce, tx.r.hex(), tx.s.hex(), tx.v))
                    print('Inserting tx {}'.format(tx.hash.hex()[:5]))
                    inserted_tx = True
                except sqlite3.IntegrityError as e:
                    print(e)
                    print(tx.hash.hex())
                except OverflowError as e:
                    print(e)
                    print((block.number, tx.hash.hex(), tx['from'], tx.to, tx.value, tx.input,
                    int(block.timestamp), tx.gas, tx.gasPrice, tx.nonce, tx.r.hex(), tx.s.hex(), tx.v))
    return inserted_tx

def save_txs(txs):
    if "tokenSymbol" not in txs[0]:
        token = 'ETH'
    else:
        token = txs[0]['tokenSymbol']
    txs_tuples = [(tx["blockNumber"], tx["hash"], tx["from"], tx["to"], tx["value"], tx["timeStamp"]) for tx in txs]

    try:
        with connect() as c:
            c.executemany("INSERT OR IGNORE INTO {} VALUES (?, ?, ?, ?, ?, ?)".format(token),txs_tuples)
    except Exception as e:
        print(tx)
        print(traceback.format_exc())


    # except sqlite3.IntegrityError as e:
            #     print(e)
            #     print(tx.hash.hex())
            # except OverflowError as e:
            #     print(e)
            #     print((block.number, tx.hash.hex(), tx['from'], tx.to, tx.value, tx.input,
            #     int(block.timestamp), tx.gas, tx.gasPrice, tx.nonce, tx.r.hex(), tx.s.hex(), tx.v))

def etherscan_query_loop(token, params):
    while True:
        print('Querying etherscan...')
        print(params)
        txs = etherscan_query(params)
        save_txs(txs)
        params['endblock'] = txs[-1]["blockNumber"]
        print('Successfully saved {} transactions for {} from block {} to {}'.format(len(txs), token, txs[0]['blockNumber'], txs[-1]['blockNumber']))
        if len(txs) != 10000:
            break

@sleep_and_retry
@limits(calls=3, period=1)
def etherscan_query(params):
    base_url = "http://api.etherscan.io/api?"
    resp = requests.get(base_url + urlencode(params)).json()
    if resp['status'] == "1":
        return resp['result']
    else:
        print('Ethersan API error')
        print(resp['message'])
        return None
