from flask import Flask, request, jsonify
import json
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mock_jwt_secret'
PORT = 3000

# 数据存储路径
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# 初始化数据
def init_data():
    # 如果用户数据文件不存在，创建初始数据
    if not os.path.exists(USERS_FILE):
        initial_users = [
            {
                "user_id": 1,
                "username": "admin",
                "password": "Admin123!",
                "email": "admin@example.com",
                "phone": "13800138001",
                "avatar": "http://example.com/avatar/1.jpg",
                "create_time": "2023-01-01 10:00:00",
                "update_time": "2023-01-02 15:30:00",
                "role": "admin",
                "status": 1
            },
            {
                "user_id": 2,
                "username": "test_user",
                "password": "Test123!",
                "email": "test@example.com",
                "phone": "13800138000",
                "avatar": "http://example.com/avatar/2.jpg",
                "create_time": "2023-01-02 10:00:00",
                "update_time": "2023-01-03 15:30:00",
                "role": "user",
                "status": 1
            }
        ]
        with open(USERS_FILE, 'w') as f:
            json.dump(initial_users, f, indent=2)


# 读取用户数据
def get_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取用户数据失败: {e}")
        return []


# 保存用户数据
def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        return True
    except Exception as e:
        print(f"保存用户数据失败: {e}")
        return False


# 生成JWT令牌
def generate_token(user):
    return jwt.encode(
        {
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(hours=1)
        },
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )


# 验证令牌
def verify_token(token):
    if not token:
        return None

    try:
        decoded = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# 令牌验证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({
                'code': 40009,
                'message': '令牌无效'
            }), 401

        decoded = verify_token(token)

        if not decoded:
            return jsonify({
                'code': 40009,
                'message': '令牌无效'
            }), 401

        return f(decoded, *args, **kwargs)

    return decorated


# 1. 用户注册接口
@app.post('/api/v1/users/register')
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    phone = data.get('phone')

    users = get_users()

    # 验证用户名是否已存在
    if any(user['username'] == username for user in users):
        return jsonify({
            'code': 40001,
            'message': '用户名已存在'
        }), 400

    # 验证邮箱是否已注册
    if any(user['email'] == email for user in users):
        return jsonify({
            'code': 40002,
            'message': '邮箱已注册'
        }), 400

    # 验证密码格式（至少8位，包含字母和数字）
    if not (8 <= len(password) <= 20 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        return jsonify({
            'code': 40003,
            'message': '密码格式不正确，需包含字母和数字，长度8-20位'
        }), 400

    # 验证邮箱格式
    if not (email and '@' in email and '.' in email):
        return jsonify({
            'code': 40004,
            'message': '邮箱格式不正确'
        }), 400

    # 生成新用户ID
    new_user_id = max(user['user_id'] for user in users) + 1 if users else 1

    # 创建新用户
    new_user = {
        'user_id': new_user_id,
        'username': username,
        'password': password,  # 实际应用中应该加密存储
        'email': email,
        'phone': phone or '',
        'avatar': f'http://example.com/avatar/{new_user_id}.jpg',
        'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'role': 'user',
        'status': 1
    }

    # 添加新用户到数据
    users.append(new_user)
    save_users(users)

    # 返回注册成功响应
    return jsonify({
        'code': 200,
        'message': '注册成功',
        'data': {
            'user_id': new_user['user_id'],
            'username': new_user['username'],
            'email': new_user['email'],
            'create_time': new_user['create_time']
        }
    }), 200


# 2. 用户登录接口（对应文档第2节）
@app.post('/api/v1/users/login')
def login():
    """
    用户登录获取token接口
    文档要求：
    - 接口URL: POST /api/v1/users/login
    - 必填参数: username, password
    - 可选参数: remember_me (默认false)
    - 成功响应: code=200, 包含token和user_info
    - 错误码: 40005(用户名/密码错误), 40006(账号禁用)
    """
    print("接收到登录请求")
    try:
        # 解析请求参数
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        remember_me = data.get('remember_me', False)  # 文档要求：可选，默认false
        print(f"登录参数: username={username}")

        # 读取用户数据（增加文件操作异常处理）
        try:
            users = get_users()
        except Exception as e:
            print(f"读取用户数据异常: {e}")
            return jsonify({
                'code': 500,
                'message': '服务器内部错误，用户数据读取失败',
                'error_detail': str(e)
            }), 500

        # 查找用户（文档错误码40005）
        user = next((u for u in users if u['username'] == username), None)
        if not user:
            print(f"登录失败: 用户名 {username} 不存在")
            return jsonify({
                'code': 40005,
                'message': '用户名或密码错误'
            }), 400

        # 验证密码（文档错误码40005）
        if user['password'] != password:
            print(f"登录失败: 密码错误 for user: {username}")
            return jsonify({
                'code': 40005,
                'message': '用户名或密码错误'
            }), 400

        # 检查账号状态（文档错误码40006）
        if user['status'] != 1:
            print(f"登录失败: 账号 {username} 已被禁用")
            return jsonify({
                'code': 40006,
                'message': '账号已被禁用'
            }), 400

        # 生成令牌（符合文档响应结构）
        try:
            token = generate_token(user)
        except jwt.exceptions.PyJWTError as e:
            print(f"登录接口JWT处理异常: {e}")
            return jsonify({
                'code': 500,
                'message': '登录处理失败，令牌生成异常',
                'error_detail': str(e)
            }), 500

        print(f"登录成功: user {username} (ID: {user['user_id']})")
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'token': token,
                'token_type': 'Bearer',  # 文档要求
                'expires_in': 3600,  # 文档要求：过期时间1小时
                'user_info': {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            }
        }), 200

    except Exception as e:
        import traceback
        print(f"登录接口全局异常: {e}")
        print(traceback.format_exc())
        return jsonify({
            'code': 500,
            'message': '登录处理失败，请稍后再试',
            'error_detail': str(e)
        }), 500

# 3. 获取用户信息接口
@app.get('/api/v1/users/<int:user_id>')
@token_required
def get_user(decoded, user_id):
    users = get_users()
    user = next((u for u in users if u['user_id'] == user_id), None)

    if not user:
        return jsonify({
            'code': 40007,
            'message': '用户不存在'
        }), 404

    # 检查权限：只能访问自己的信息或管理员访问所有
    if decoded['user_id'] != user_id and decoded['role'] != 'admin':
        return jsonify({
            'code': 40008,
            'message': '无权限访问'
        }), 403

    # 返回用户信息
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'phone': user['phone'],
            'avatar': user['avatar'],
            'create_time': user['create_time'],
            'update_time': user['update_time'],
            'role': user['role'],
            'status': user['status']
        }
    }), 200


# 4. 更新用户信息接口
@app.put('/api/v1/users/<int:user_id>')
@token_required
def update_user(decoded, user_id):
    data = request.get_json()
    email = data.get('email')
    phone = data.get('phone')
    avatar = data.get('avatar')
    password = data.get('password')

    users = get_users()
    user_index = next((i for i, u in enumerate(users) if u['user_id'] == user_id), None)

    if user_index is None:
        return jsonify({
            'code': 40007,
            'message': '用户不存在'
        }), 404

    # 检查权限：只能更新自己的信息或管理员更新所有
    if decoded['user_id'] != user_id and decoded['role'] != 'admin':
        return jsonify({
            'code': 40008,
            'message': '无权限访问'
        }), 403

    # 验证参数格式
    if email and not (email and '@' in email and '.' in email):
        return jsonify({
            'code': 40010,
            'message': '邮箱格式不正确'
        }), 400

    if password and not (
            8 <= len(password) <= 20 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        return jsonify({
            'code': 40010,
            'message': '密码格式不正确，需包含字母和数字，长度8-20位'
        }), 400

    # 更新用户信息
    user = users[user_index]
    if email is not None:
        user['email'] = email
    if phone is not None:
        user['phone'] = phone
    if avatar is not None:
        user['avatar'] = avatar
    if password is not None:
        user['password'] = password  # 实际应用中应该加密
    user['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 保存更新
    users[user_index] = user
    save_users(users)

    # 返回更新成功响应
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': {
            'user_id': user['user_id'],
            'update_time': user['update_time']
        }
    }), 200


# 5. 删除用户接口
@app.delete('/api/v1/users/<int:user_id>')
@token_required
def delete_user(decoded, user_id):
    reason = request.args.get('reason')  # 删除原因，可选

    users = get_users()
    user_index = next((i for i, u in enumerate(users) if u['user_id'] == user_id), None)

    if user_index is None:
        return jsonify({
            'code': 40007,
            'message': '用户不存在'
        }), 404

    user = users[user_index]

    # 检查权限：只能删除自己的信息或管理员删除非管理员用户
    if not (
        (decoded['role'] == 'admin' and user['role'] != 'admin') or
        (decoded['user_id'] == user_id and decoded['role'] == 'user')
    ):
        return jsonify({
            'code': 40008,
            'message': '无权限访问'
        }), 403

    # 不能删除管理员用户
    if user['role'] == 'admin':
        return jsonify({
            'code': 40011,
            'message': '不能删除管理员用户'
        }), 400

    # 删除用户
    users.pop(user_index)
    save_users(users)

    # 返回删除成功响应
    return jsonify({
        'code': 200,
        'message': '删除成功',
        'data': {}
    }), 200


# 6.管理员专用：创建用户接口（支持创建管理员）
@app.post('/api/v1/admin/users/create')
@token_required
def create_admin_user(decoded):
    """
    管理员专用接口，用于创建指定角色的用户账号（包括管理员）
    权限要求：仅管理员可访问
    """
    # 检查是否为管理员
    if decoded['role'] != 'admin':
        return jsonify({
            'code': 40008,
            'message': '无管理员权限'
        }), 403

    # 获取请求参数
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    phone = data.get('phone', '')
    role = data.get('role', 'user')  # 默认角色为 user

    users = get_users()

    # 验证必填参数
    if not all([username, password, email]):
        return jsonify({
            'code': 40000,
            'message': '缺少必要参数，username、password、email 为必填项'
        }), 400

    # 验证用户名是否已存在
    if any(user['username'] == username for user in users):
        return jsonify({
            'code': 40001,
            'message': '用户名已存在'
        }), 400

    # 验证邮箱是否已注册
    if any(user['email'] == email for user in users):
        return jsonify({
            'code': 40002,
            'message': '邮箱已注册'
        }), 400

    # 验证密码格式
    if not (8 <= len(password) <= 20 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        return jsonify({
            'code': 40003,
            'message': '密码格式不正确，需包含字母和数字，长度8-20位'
        }), 400

    # 验证邮箱格式
    if not (email and '@' in email and '.' in email):
        return jsonify({
            'code': 40004,
            'message': '邮箱格式不正确'
        }), 400

    # 验证角色合法性
    if role not in ['user', 'admin']:
        return jsonify({
            'code': 40012,
            'message': '角色不合法，仅支持 user 或 admin'
        }), 400

    # 生成新用户ID
    new_user_id = max(user['user_id'] for user in users) + 1 if users else 1

    # 创建新用户
    new_user = {
        'user_id': new_user_id,
        'username': username,
        'password': password,  # 实际应用中应该加密存储
        'email': email,
        'phone': phone,
        'avatar': f'http://example.com/avatar/{new_user_id}.jpg',
        'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'role': role,
        'status': 1
    }

    # 添加新用户到数据
    users.append(new_user)
    save_users(users)

    # 返回创建成功响应
    return jsonify({
        'code': 200,
        'message': '用户创建成功',
        'data': {
            'user_id': new_user['user_id'],
            'username': new_user['username'],
            'email': new_user['email'],
            'role': new_user['role'],
            'create_time': new_user['create_time']
        }
    }), 200

if __name__ == '__main__':
    init_data()
    print(f'Mock服务已启动，运行在 http://localhost:{PORT}')
    print('接口文档:')
    print('1. 注册: POST /api/v1/users/register')
    print('2. 登录: POST /api/v1/users/login')
    print('3. 获取用户信息: GET /api/v1/users/:user_id')
    print('4. 更新用户信息: PUT /api/v1/users/:user_id')
    print('5. 删除用户: DELETE /api/v1/users/:user_id')
    print('6. 管理员创建：POST /api/v1/admin/users/create')
    app.run(port=PORT, debug=True)