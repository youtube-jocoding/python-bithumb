# private_api.py
import requests
import jwt
import uuid
import time
import hashlib
from urllib.parse import urlencode
import json
from .public_api import BithumbAPIException

class Bithumb:
    BASE_URL = "https://api.bithumb.com"

    def __init__(self, access_key: str, secret_key: str):
        """
        Bithumb Private API 접근을 위한 클래스.
        
        Parameters
        ----------
        access_key : str
            Bithumb에서 발급받은 Access Key
        secret_key : str
            Bithumb에서 발급받은 Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key

    def _create_token(self, query_hash=None, query_hash_alg=None):
        """
        JWT 토큰 생성 메소드.
        
        Parameters
        ----------
        query_hash : str, optional
            POST 요청 시 body를 해싱한 값
        query_hash_alg : str, optional
            해시 알고리즘 (SHA512)
        
        Returns
        -------
        str
            'Bearer {jwt_token}' 형태의 인증 토큰
        """
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000)
        }

        if query_hash and query_hash_alg:
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = query_hash_alg

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return 'Bearer ' + token

    def _handle_response(self, response):
        """
        API 응답을 처리하고 오류를 적절히 처리합니다.
        
        Args:
            response: requests Response 객체
            
        Returns:
            파싱된 JSON 응답 데이터
            
        Raises:
            BithumbAPIException: API가 오류를 반환하는 경우
        """
        if not (200 <= response.status_code < 300):
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    error_info = error_data['error']
                    if isinstance(error_info, dict):
                        error_name = error_info.get('name', 'Unknown error code')
                        error_message = error_info.get('message', 'No error message provided')
                        error_msg = f"Error {error_name}: {error_message}"
                    else:
                        error_msg = str(error_info)
            except:
                error_msg = response.text or "Could not parse error response"
            
            raise BithumbAPIException(response.status_code, error_msg, response)
        
        return response.json()

    def _request(self, method: str, endpoint: str, params=None, data=None):
        """
        Private API 요청을 처리하는 헬퍼 메소드.
        
        Parameters
        ----------
        method : str
            HTTP 메소드 ("GET", "POST", "DELETE", ...)
        endpoint : str
            API 엔드포인트("/v1/...")
        params : dict, optional
            GET 요청 시 사용될 query parameter
        data : dict, optional
            POST/DELETE 요청 시 사용될 request body or parameters
        
        Returns
        -------
        dict or list
            API 응답으로 반환되는 JSON 데이터
        
        Raises
        ------
        BithumbAPIException
            API 요청 실패 시 상세 에러 정보와 함께 예외 발생
        """
        url = f"{self.BASE_URL}{endpoint}"

        headers = {}
        # GET 요청인 경우 query_hash 필요 없음, POST/DELETE 시 필요할 수 있음
        if method.upper() in ["POST", "DELETE", "PUT"] and data is not None:
            query = urlencode(data).encode()
            hash_object = hashlib.sha512()
            hash_object.update(query)
            query_hash = hash_object.hexdigest()

            headers['Authorization'] = self._create_token(query_hash=query_hash, query_hash_alg='SHA512')
            headers['Content-Type'] = 'application/json'
            resp = requests.request(method, url, headers=headers, params=None, data=json.dumps(data))
            return self._handle_response(resp)
        elif method.upper() == "GET":
            # GET 요청인 경우 params를 이용
            # query_hash 필요: Private API GET 요청 시에도 파라미터가 있으면 query_hash 필요
            query_str = ""
            if params:
                query_str = urlencode(params)
            if query_str:
                hash_object = hashlib.sha512()
                hash_object.update(query_str.encode())
                query_hash = hash_object.hexdigest()
                headers['Authorization'] = self._create_token(query_hash=query_hash, query_hash_alg='SHA512')
            else:
                headers['Authorization'] = self._create_token()

            resp = requests.get(url, headers=headers, params=params)
            return self._handle_response(resp)
        else:
            # data 없음 or 기타 method
            headers['Authorization'] = self._create_token()
            resp = requests.request(method, url, headers=headers, params=params, data=data)
            return self._handle_response(resp)

    def get_balances(self):
        """
        전체 계좌 조회 메소드.
        
        Returns
        -------
        list of dict
            각 화폐별 잔고 정보가 담긴 딕셔너리 리스트.
        """
        endpoint = "/v1/accounts"
        data = self._request("GET", endpoint)
        return data

    def get_balance(self, currency: str) -> float:
        """
        특정 화폐에 대한 잔고만 반환하는 헬퍼 메소드.
        
        Parameters
        ----------
        currency : str
            조회할 화폐 코드 (예: "KRW", "BTC")

        Returns
        -------
        float
            해당 화폐의 주문 가능 잔고. 화폐가 없거나 0일 경우 0.0 반환.
        """
        balances = self.get_balances()
        for bal in balances:
            if bal['currency'] == currency:
                return float(bal['balance'])
        return 0.0

    def buy_limit_order(self, ticker: str, price: float, volume: float):
        """
        지정가 매수 주문.
        """
        endpoint = "/v1/orders"
        request_body = {
            "market": ticker,
            "side": "bid",
            "ord_type": "limit",
            "price": str(price),
            "volume": str(volume)
        }
        return self._request("POST", endpoint, data=request_body)

    def sell_limit_order(self, ticker: str, price: float, volume: float):
        """
        지정가 매도 주문.
        """
        endpoint = "/v1/orders"
        request_body = {
            "market": ticker,
            "side": "ask",
            "ord_type": "limit",
            "price": str(price),
            "volume": str(volume)
        }
        return self._request("POST", endpoint, data=request_body)

    def buy_market_order(self, ticker: str, krw_amount: float):
        """
        시장가 매수 주문.
        """
        endpoint = "/v1/orders"
        request_body = {
            "market": ticker,
            "side": "bid",
            "ord_type": "price",
            "price": str(krw_amount)
        }
        return self._request("POST", endpoint, data=request_body)

    def sell_market_order(self, ticker: str, volume: float):
        """
        시장가 매도 주문.
        """
        endpoint = "/v1/orders"
        request_body = {
            "market": ticker,
            "side": "ask",
            "ord_type": "market",
            "volume": str(volume)
        }
        return self._request("POST", endpoint, data=request_body)

    ### 새로 추가된 함수들 ###

    def get_order_chance(self, market: str):
        """
        주문 가능 정보 조회
        
        Parameters
        ----------
        market : str
            마켓 ID (예: "KRW-BTC")
        
        Returns
        -------
        dict
            주문 가능 정보 JSON
        """
        endpoint = "/v1/orders/chance"
        params = {"market": market}
        return self._request("GET", endpoint, params=params)

    def get_order(self, uuid: str):
        """
        개별 주문 조회
        
        Parameters
        ----------
        uuid : str
            주문 UUID
        
        Returns
        -------
        dict
            주문 정보 JSON
        """
        endpoint = "/v1/order"
        params = {"uuid": uuid}
        return self._request("GET", endpoint, params=params)

    def get_orders(self, market=None, uuids=None, state=None, states=None, page=1, limit=100, order_by='desc'):
        """
        주문 리스트 조회
        
        Parameters
        ----------
        market : str, optional
            마켓 ID
        uuids : list of str, optional
            주문 UUID의 목록
        state : str, optional
            단일 주문 상태(wait, watch, done, cancel)
        states : list of str, optional
            주문 상태 목록
        page : int, optional (default 1)
            페이지 수
        limit : int, optional (default 100)
            개수 제한 (최대 100)
        order_by : str, optional (default 'desc')
            정렬방식 ('asc' or 'desc')
        
        Returns
        -------
        list of dict
            주문 정보 리스트
        """
        endpoint = "/v1/orders"
        params = {}
        if market:
            params["market"] = market
        if state:
            params["state"] = state
        if states:
            # states[] 파라미터 형태로 전송 필요
            # urlencode 시 states[]=<value>로 보내야 함
            # 여기서는 수동으로 query_hash 생성 시 필요하니 그대로 params에 담을 수 없음
            # 방법1: states를 params에 넣지 않고 아래 _request 전에 별도 처리
            # 하지만 _request 함수가 query_hash를 다루므로 여기서 states를 처리하는 특수 로직 필요
            # states[] 파라미터 전송 방식:
            # uuids와 유사하게 별도 query 문자열 생성
            pass
        if uuids:
            # uuids[] 형태로 보내야 하므로 마찬가지로 별도 처리 필요
            pass
        # 나머지 파라미터
        params["page"] = page
        params["limit"] = limit
        params["order_by"] = order_by

        # states, uuids가 list일 경우 수동으로 query 생성
        query_list = []
        if params:
            query_list.append(urlencode(params))
        if uuids and isinstance(uuids, list):
            uuid_queries = '&'.join([f'uuids[]={u}' for u in uuids])
            query_list.append(uuid_queries)
        if states and isinstance(states, list):
            state_queries = '&'.join([f'states[]={s}' for s in states])
            query_list.append(state_queries)

        final_query = '&'.join(query_list)

        # final_query를 기반으로 query_hash 생성 필요
        hash_object = hashlib.sha512()
        hash_object.update(final_query.encode())
        query_hash = hash_object.hexdigest()

        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        headers = {
            'Authorization': 'Bearer ' + token
        }

        url = f"{self.BASE_URL}/v1/orders?{final_query}"
        resp = requests.get(url, headers=headers)
        return self._handle_response(resp)

    def cancel_order(self, order_uuid: str):
        """
        주문 취소 접수
        
        Parameters
        ----------
        order_uuid : str
            취소할 주문의 UUID
        
        Returns
        -------
        dict
            취소된 주문 정보 JSON
        """
        endpoint = "/v1/order"
        params = {"uuid": order_uuid}

        query = urlencode(params).encode()
        hash_object = hashlib.sha512()
        hash_object.update(query)
        query_hash = hash_object.hexdigest()

        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        headers = {
            'Authorization': 'Bearer ' + token
        }

        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.delete(url, headers=headers, params=params)
        return self._handle_response(resp)