import requests
from utils.loader import YamlLoader

class APIClient:
    def __init__(self):
        self.config = YamlLoader.get_config()
        self.base_url = self.config.get("base_url","http://127.0.0.1:3000")
        self.session = requests.session()  #requests.Session() 是 requests 库（Python 常用的 HTTP 请求库）提供的会话对象，它能保持请求之间的连接、Cookie 等状态。



    def _set_headers(self):  #定义一个内置更新(基础请求头)请求头的方法
        self.session.headers.update(
            {
                "Content-Type" : "application/json",
                "Accept" : "application/json"
            }
        )



    def authenticate(self,token):  #鉴权请求头
        self.session.headers.update(
            {"Authorization": f"Bearer {token}"
             })








    def get(self,endpoint,param = None,**kwargs):
        """定义get请求方法"""
        url = f"{self.base_url}{endpoint}"
        # print(f"发送的请求头:{kwargs.get('headers')}]")
        print(url)
        return self.session.get(url,params=param,**kwargs)

    def post(self,endpoint,json = None,data = None,**kwargs):
        """定义post方法"""
        url = f"{self.base_url}{endpoint}"
        return self.session.post(url,json=json,data=data,**kwargs)

    def put(self,endpoint,json = None,data = None,**kwargs):
        """定义put方法"""
        url = f"{self.base_url}{endpoint}"
        return self.session.put(url,json=json,data=data,**kwargs)

    def delete(self,endpoint,json= None,**kwargs):
        """定义delete方法"""
        url = f"{self.base_url}{endpoint}"
        return self.session.delete(url,json=json,**kwargs)

