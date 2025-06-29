from operator import index

import pytest
from api.user_management import UserManagementAPI
from utils.loader import YamlLoader
from common.parameter_json import Parameter
from common.generate_parameter import Generate
import copy
yaml_data =YamlLoader()

@pytest.fixture(scope= "session")
def api_client():
    return UserManagementAPI()

@pytest.fixture(scope="session")
def registered_users(api_client):
    """注册用户返回账号密码列表"""
    users = []
    for _ in range(5):
        params = Parameter.register_parameters()
        resp = api_client.register(params)
        resp_json = resp.json()
        assert resp_json.get("code") == 200
        assert resp_json.get("message") == "注册成功"
        data = resp_json.get("data", {})
        assert isinstance(data.get("user_id"), int)
        assert data.get("create_time") is not None
        users.append({
            "username": params["username"],
            "password": params["password"]
        })

    yield users  #提供给测试用例


@pytest.fixture(scope="session")
def login_info(api_client, registered_users):
    """登录接口返回用户登录的token"""
    login_info_list = []
    for i in range(5):
        params = Parameter.login_parameters()
        params["username"] = registered_users[i]["username"]
        params["password"] = registered_users[i]["password"]
        # print("9"* 50)
        # print(params)
        # print("9" * 50)
        resp = api_client.login(params)
        resp_json = resp.json()
        assert resp_json["code"] == 200, f"登录失败：{resp_json}"
        assert resp_json["message"] == "登录成功"
        assert "token" in resp_json["data"]
        token = resp_json["data"]["token"]
        user_id = resp_json["data"]["user_info"]["user_id"]
        role = resp_json["data"]["user_info"]["role"]
        login_info_list.append({
            "token":token,
            "user_id":user_id,
            "role":role
        })
    # print(login_info_list)
    yield login_info_list


@pytest.fixture(scope="session")
def obtain_avatar(api_client,login_info):
    """用户头像url返回"""
    avatar_list = []
    for i in range(5):
        token = login_info[i]["token"]
        user_id = login_info[i]["user_id"]
        api_client.authenticate(token)
        resp = api_client.obtain(user_id)
        resp_json = resp.json()
        avatar = resp_json["data"]["avatar"]
        avatar_list.append({"avatar": avatar})
    print(avatar_list)


    yield avatar_list


@pytest.fixture(scope="session")
def admin_token(api_client,login_info):
    """获取普通管理员token"""
    param = {
        "username": "admin",
         "password": "Admin123!"
    }
    resp = api_client.login(param)
    resp_json =resp.json()
    token = resp_json["data"]["token"]
    print(f"获取默认管理员token：{token}")
    return token


@pytest.fixture(scope="session")
def create_token(api_client,admin_token):
    print()
    api_client.authenticate(admin_token)
    params = Parameter.admin_parameters()
    api_client.admin(params)

    login_data = {"username":params["username"],
                  "password":params["password"]}

    resp = api_client.login(login_data)
    resp_json = resp.json()
    token = resp_json["data"]["token"]
    print(f"获取新添管理员token：{token}")
    yield token







# @pytest.mark.skip
# @pytest.mark.parametrize("username",yaml_data.get_data("boundary_data")["username"])
@pytest.mark.parametrize("username",[Generate.generate_username() for _ in range(5)])
def test_register(api_client,username):
    """"测试注册接口"""
    # params = register_parameter()
    params = Parameter.register_parameters()
    # params["username"] = username
    resp = api_client.register(register_data= params)
    resp_json = resp.json()
    print("*" * 50)
    print(resp_json)
    print("*" * 50)
    assert resp_json.get("code") == 200
    assert resp_json.get("message") == "注册成功"
    #这种方法不行（只用响应结构稳定时候能用）
    # assert resp_json["data"]["user_id"] == 123
    # assert resp_json["data"]["create_time"] is not None
    #用这种方法
    data = resp_json.get("data",{})
    assert isinstance(data.get("user_id"),int)
    assert data.get("create_time") is not None



# @pytest.mark.skip
@pytest.mark.parametrize("user_index",range(5))
def test_login(api_client,registered_users,user_index):  #registered_users被注入测试用例里面后，返回的就是users列表
    """验证登录接口"""
    params = Parameter.login_parameter()
    user = registered_users[user_index]
    params["username"] = user["username"]
    params["password"] = user["password"]
    resp = api_client.login(params)
    print("登录响应:", resp.json())
    resp_json = resp.json()
    assert resp_json["code"] == 200,f"登录失败：{resp_json}"
    assert resp_json["message"] == "登录成功"
    assert "token" in resp_json["data"]
    assert resp_json["data"]["user_info"]["username"] == user["username"]


@pytest.mark.parametrize("index",range(5))
def test_obtain(api_client, login_info, index):
    """验证获取用户信息接口"""
    token = login_info[index]["token"]
    user_id = login_info[index]["user_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"准备传递的 headers: {headers}")
    api_client.authenticate(token)
    resp = api_client.obtain(user_id)
    resp_json = resp.json()
    print("-" * 50)
    print(resp_json)
    print("-" * 50)
    assert resp_json["code"] == 200, f"获取失败:{resp_json}"
    assert resp_json["message"] == "获取成功"
    assert resp_json["data"]["status"] == 1



@pytest.mark.parametrize("index",range(5))
def test_update(api_client,login_info,index,obtain_avatar):
    token = login_info[index]["token"]
    user_id = login_info[index]["user_id"]
    api_client.authenticate(token)
    params = Parameter.update_parameters()
    params["avatar"] = obtain_avatar[index]["avatar"]
    print("*" * 80)
    print(params)
    print("*" * 80)
    resp = api_client.update(user_id,params)
    resp_json = resp.json()
    assert resp_json["code"] == 200,f"断言出错，返回的json数据为：{resp_json}"
    assert resp_json["message"] == "更新成功"
    assert resp_json["data"]["user_id"] == user_id
    assert resp_json["data"]["update_time"] is not None


@pytest.mark.parametrize("index",range(5))
def test_delete(api_client,login_info,index):
    user_info = login_info[index]
    token = user_info["token"]
    user_id = user_info["user_id"]
    api_client.authenticate(token)
    params = {"reason":"用户不想要了"}
    resp = api_client.delete_user(user_id,params)
    resp_json = resp.json()
    assert resp_json["code"] == 200,f"断言出错，返回的json数据为：{resp_json}"
    assert resp_json["message"] == "删除成功"

@pytest.mark.parametrize("index",range(5))
def test_admin_delete(api_client,admin_token,login_info,index):
    api_client.authenticate(admin_token)
    user_id = login_info[index]["user_id"]
    param = {"reason":"管理员清除"}
    resp = api_client.delete_user(user_id,param)
    resp_json = resp.json()
    print(resp_json)