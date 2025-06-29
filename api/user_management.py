from keyword import kwlist

from api.client import APIClient

class UserManagementAPI(APIClient):
    def __init__(self):
        super().__init__()
        self.endpoint = {
            "register": "/api/v1/users/register",
            "login": "/api/v1/users/login",
            "obtain": "/api/v1/users/{user_id}",
            "update": "/api/v1/users/{user_id}",
            "delete": "/api/v1/users/{user_id}",
            "admin": "/api/v1/admin/users/create"
        }

    def register(self,register_data):
        """用户注册"""
        return self.post(self.endpoint["register"],json=register_data)


    def login(self,login_data):
        """用户登录"""
        return self.post(self.endpoint["login"],json=login_data)

    def obtain(self,user_id):
        """获取用户信息"""
        endpoint = self.endpoint["obtain"].format(user_id = user_id)
        return self.get(endpoint)

    def update(self,user_id,update_data):
        """更新用户信息"""
        endpoint = self.endpoint["update"].format(user_id = user_id)
        return self.put(endpoint,json=update_data)

    def delete_user(self,user_id,reason):
        """"删除用户信息"""
        endpoint = self.endpoint["delete"].format(user_id = user_id)
        return self.delete(endpoint,json=reason)


    def admin(self,admin_data):
        """管理员注册"""
        return self.post(self.endpoint["admin"],json=admin_data)

