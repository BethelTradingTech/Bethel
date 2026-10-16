"""Run in the hosting service shell. Read-only Binance connectivity diagnostic.

Optional runtime secrets: BINANCE_SPOT_API_KEY and BINANCE_SPOT_API_SECRET.
Never accepts credentials as command-line arguments and never prints them.
No order, transfer, withdrawal, alternate-host, or proxy functionality.
"""
import hashlib
import hmac
import json
import os
from urllib.parse import urlencode
import requests

BASE = 'https://api.binance.com'


def get(path, params=None, headers=None):
    try:
        response = requests.get(BASE + path, params=params, headers=headers,
                                timeout=(5, 15), allow_redirects=False)
    except requests.RequestException:
        return None, {'status': 'network_error'}
    if response.status_code != 200:
        # Never print exception URLs, response bodies or request headers: they
        # can contain signed queries or account information.
        return None, {'status': 'http_error', 'http_status': response.status_code,
                      'action': 'Check Binance service eligibility and hosting access; do not bypass restrictions.'}
    try:
        return response.json(), None
    except ValueError:
        return None, {'status': 'invalid_response'}


def check():
    result = {'mode': 'read_only', 'order_execution': False}
    server, error = get('/api/v3/time')
    if error:
        return dict(result, connectivity=error, account='not_checked')
    if not isinstance(server, dict) or not isinstance(server.get('serverTime'), int):
        return dict(result, connectivity={'status': 'invalid_server_time'}, account='not_checked')
    result['connectivity'] = {'status': 'ok'}
    key = os.environ.get('BINANCE_SPOT_API_KEY', '').strip()
    secret = os.environ.get('BINANCE_SPOT_API_SECRET', '').strip()
    if not key or not secret:
        return dict(result, account={'status': 'credentials_not_configured'})
    query = urlencode({'timestamp': server['serverTime'], 'recvWindow': 5000})
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    account, error = get('/api/v3/account', query + '&signature=' + signature,
                         {'X-MBX-APIKEY': key})
    if error:
        return dict(result, account=error)
    if not isinstance(account, dict) or not isinstance(account.get('balances'), list):
        return dict(result, account={'status': 'invalid_account_response'})
    result['account'] = {'status': 'connected', 'can_trade': bool(account.get('canTrade')),
                         'account_type': account.get('accountType'),
                         'balance_asset_count': len(account['balances'])}
    return result


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
