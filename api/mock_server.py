from flask import Flask, request, jsonify
import json
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mock_jwt_secret'
PORT = 3000
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 初始化数据
def init_data():
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
                "phone": "13800138002",
                "avatar": "http://example.com/avatar/2.jpg",
                "create_time": "2023-02-01 14:00:00",
                "update_time": "2023-02-02 16:20:00",
                "role": "user",
                "status": 1
            }
        ]
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_users, f, ensure_ascii=False, indent=2)

# JWT 装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # 从请求头获取 token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = next((user for user in get_users() if user['user_id'] == data['user_id']), None)
            if not current_user:
                return jsonify({"message": "Invalid token!"}), 401
            # 将当前用户注入请求
            request.current_user = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401
        return f(*args, **kwargs)
    return decorated

# 获取所有用户
def get_users():
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 保存用户数据
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# 注册接口
@app.route('/api/v1/users/register', methods=['POST'])
def register():
    data = request.get_json()
    users = get_users()
    # 检查用户名是否已存在
    if any(user['username'] == data['username'] for user in users):
        return jsonify({"message": "Username already exists!"}), 400
    # 检查邮箱是否已存在
    if any(user['email'] == data['email'] for user in users):
        return jsonify({"message": "Email already exists!"}), 400
    # 生成新用户 ID
    new_user_id = max(user['user_id'] for user in users) + 1 if users else 1
    new_user = {
        "user_id": new_user_id,
        "username": data['username'],
        "password": data['password'],
        "email": data['email'],
        "phone": data.get('phone', ''),
        "avatar": data.get('avatar', ''),
        "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "role": "user",
        "status": 1
    }
    users.append(new_user)
    save_users(users)
    # 生成 JWT
    token = jwt.encode({
        "user_id": new_user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return jsonify({"message": "User registered successfully!", "token": token}), 201

# 登录接口
@app.route('/api/v1/users/login', methods=['POST'])
def login():
    data = request.get_json()
    users = get_users()
    user = next((user for user in users if user['username'] == data['username'] and user['password'] == data['password']), None)
    if not user:
        return jsonify({"message": "Invalid credentials!"}), 401
    # 生成 JWT
    token = jwt.encode({
        "user_id": user['user_id'],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return jsonify({"message": "Login successful!", "token": token}), 200

# 获取当前用户信息
@app.route('/api/v1/users/me', methods=['GET'])
@token_required
def get_current_user():
    return jsonify(request.current_user), 200

# 更新用户信息
@app.route('/api/v1/users/me', methods=['PUT'])
@token_required
def update_current_user():
    data = request.get_json()
    users = get_users()
    user_index = next((i for i, user in enumerate(users) if user['user_id'] == request.current_user['user_id']), None)
    if user_index is None:
        return jsonify({"message": "User not found!"}), 404
    # 更新允许的字段
    update_fields = ['username', 'email', 'phone', 'avatar']
    for field in update_fields:
        if field in data:
            users[user_index][field] = data[field]
    # 更新时间
    users[user_index]['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_users(users)
    return jsonify(users[user_index]), 200

# 删除当前用户
@app.route('/api/v1/users/me', methods=['DELETE'])
@token_required
def delete_current_user():
    users = get_users()
    # 保留 admin 用户，禁止删除
    if request.current_user['role'] == 'admin':
        return jsonify({"message": "Admin user cannot be deleted!"}), 403
    users = [user for user in users if user['user_id'] != request.current_user['user_id']]
    save_users(users)
    return jsonify({"message": "User deleted successfully!"}), 200

# 管理员创建用户（示例）
@app.route('/api/v1/users', methods=['POST'])
@token_required
def create_user():
    # 检查是否是管理员
    if request.current_user['role'] != 'admin':
        return jsonify({"message": "Permission denied!"}), 403
    data = request.get_json()
    users = get_users()
    # 检查用户名是否已存在
    if any(user['username'] == data['username'] for user in users):
        return jsonify({"message": "Username already exists!"}), 400
    # 生成新用户 ID
    new_user_id = max(user['user_id'] for user in users) + 1 if users else 1
    new_user = {
        "user_id": new_user_id,
        "username": data['username'],
        "password": data['password'],
        "email": data['email'],
        "phone": data.get('phone', ''),
        "avatar": data.get('avatar', ''),
        "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "role": data.get('role', 'user'),
        "status": 1
    }
    users.append(new_user)
    save_users(users)
    return jsonify({"message": "User created successfully!"}), 201

# 初始化数据并启动服务
if __name__ == "__main__":
    init_data()
    # 关键修复：绑定 0.0.0.0，确保 GitHub Actions 能访问
    app.run(host='0.0.0.0', port=PORT, debug=True)
