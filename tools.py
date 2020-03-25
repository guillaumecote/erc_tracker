import requests
import os
import json
import smtplib
import ssl
from twilio.rest import TwilioRestClient



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
    with connect() as c:
        for tx in block.transactions:
            if tx.to in (c.address for c in coins):
                try:
                    c.execute("INSERT INTO transactions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(block.number, tx.hash.hex(), tx['from'], tx.to, str(tx.value), tx.input,
                    int(block.timestamp), tx.gas, tx.gasPrice, tx.nonce, tx.r.hex(), tx.s.hex(), tx.v))
                    print('Inserting tx {}'.format(tx.hash.hex()[:5]))
                except sqlite3.IntegrityError as e:
                    print(e)
                    print(tx.hash.hex())
                except OverflowError as e:
                    print(e)
                    print((block.number, tx.hash.hex(), tx['from'], tx.to, tx.value, tx.input,
                    int(block.timestamp), tx.gas, tx.gasPrice, tx.nonce, tx.r.hex(), tx.s.hex(), tx.v))
