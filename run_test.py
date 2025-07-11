import pytest
import os
from datetime import datetime
import requests
import json
import configparser
import base64
import subprocess
import socket
from time import sleep
import schedule
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def load_config():
    """加载配置文件，适配项目中config/config.ini的路径"""
    # 获取当前脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 拼接出config/config.ini的完整路径
    config_path = os.path.join(current_dir, "config", "config.ini")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在，请检查路径是否正确")

    config = configparser.ConfigParser()
    config.read(config_path,encoding="utf-8")
    return config

def generate_allure_report(report_path):
    """生成Allure报告到指定目录"""
    allure_results_dir = os.path.join(report_path, 'allure-results')
    allure_report_dir = os.path.join(report_path, 'html')
    
    if not os.path.exists(allure_results_dir):
        print(f"Allure结果目录不存在: {allure_results_dir}")
        return
    
    try:
        # 使用完整路径生成报告
        subprocess.run(
            f"allure generate {allure_results_dir} -o {allure_report_dir} --clean",
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        print(f"Allure报告生成成功: {allure_report_dir}")
        return allure_report_dir
    except subprocess.CalledProcessError as e:
        print(f"Allure报告生成失败: {e.stderr}")
        return None


def start_temp_server(report_html_path):
    """启动临时HTTP服务器并返回可访问的URL"""
    if not os.path.exists(report_html_path):
        print(f"报告目录不存在: {report_html_path}")
        return None
        
    # 获取本机局域网IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()

    # 启动服务器（后台运行）
    port = 8000
    cmd = f"python -m http.server {port} --directory {report_html_path} > server.log 2>&1 &"
    subprocess.Popen(cmd, shell=True)

    # 等待服务器启动
    sleep(2)

    # 返回可访问的链接
    return f"http://{local_ip}:{port}/index.html"

def run_tests(config):
    """执行测试并生成报告"""
    # 创建带时间戳的报告目录
    report_dir = config.get('report', 'directory', fallback='reports')
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(report_dir, f'report_{timestamp}')
    os.makedirs(report_path, exist_ok=True)
    
    # 测试结果输出到报告目录下的 allure-results（与报告生成路径一致）
    allure_results_path = os.path.join(report_path, 'allure-results')
    os.makedirs(allure_results_path, exist_ok=True)
    
    # 执行测试
    pytest_args = [
        'tests/',
        f'--alluredir={allure_results_path}',  # 输出到带时间戳的目录
        '-v',
        '-s'
    ]
    exit_code = pytest.main(pytest_args)
    
    # 生成报告（路径已对齐）
    allure_report_dir = generate_allure_report(report_path)
    
    # 其他代码保持不变...
    
    # 生成在线访问链接
    report_url = None
    if allure_report_dir:
        report_url = start_temp_server(allure_report_dir)
        if report_url:
            print(f"测试报告已生成: {report_url}")
        else:
            print("无法启动报告服务器")
    else:
        print("无法生成报告链接")

    # 发送通知
    platform = config.get('notification', 'platform', fallback='dingtalk').lower()
    if platform == 'dingtalk':
        send_dingtalk_message(report_url, config, exit_code, report_path)
    elif platform == 'wechat':
        send_wechat_message(report_url, config, exit_code, report_path)
    else:
        print(f"不支持的通知平台: {platform}")

    return exit_code    


def send_dingtalk_message(report_url, config, exit_code, report_path):
    """发送钉钉消息通知"""
    webhook_url = config.get('dingtalk', 'webhook')
    secret = config.get('dingtalk', 'secret', fallback=None)

    # 构建消息内容
    message_title = "📊 自动化测试报告"
    test_summary = get_test_summary(report_path)

    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": message_title,
            "text": f"""
# {message_title}
- **执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **执行结果**: {'✅ 全部通过' if exit_code == 0 else '❌ 存在失败'}
- **测试总数**: {test_summary.get('total', '未知')}
- **通过数量**: {test_summary.get('passed', '未知')}
- **失败数量**: {test_summary.get('failed', '未知')}
- **错误数量**: {test_summary.get('broken', '未知')}
- **查看详情**: [点击查看测试报告]({report_url})
"""
        },
        "at": {
            "isAtAll": config.getboolean('dingtalk', 'at_all', fallback=False)
        }
    }

    headers = {'Content-Type': 'application/json'}

    # 处理签名（如果有secret）
    if secret:
        import hmac
        import hashlib
        import time
        import urllib.parse

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url += f'&timestamp={timestamp}&sign={sign}'

    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(message))
        response.raise_for_status()  #自动检查 HTTP 请求的响应状态码，并在状态码表示请求失败时抛出异常。
        result = response.json()
        if result.get('errcode') == 0:
            print("钉钉消息发送成功")
        else:
            print(f"钉钉消息发送失败: {result.get('errmsg')}")
    except requests.RequestException as e:
        print(f"钉钉消息发送异常: {e}")


def send_wechat_message(report_url, config, exit_code, report_path):
    """发送企业微信消息通知"""
    webhook_url = config.get('wechat', 'webhook')
    test_summary = get_test_summary(report_path)

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""
# 📊 自动化测试报告
- **执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **执行结果**: {'✅ 全部通过' if exit_code == 0 else '❌ 存在失败'}
- **测试总数**: {test_summary.get('total', '未知')}
- **通过数量**: {test_summary.get('passed', '未知')}
- **失败数量**: {test_summary.get('failed', '未知')}
- **错误数量**: {test_summary.get('broken', '未知')}
- **查看详情**: [点击查看测试报告]({report_url})
"""
        }
    }

    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        result = response.json()
        if result.get('errcode') == 0:
            print("企业微信消息发送成功")
        else:
            print(f"企业微信消息发送失败: {result.get('errmsg')}")
    except requests.RequestException as e:
        print(f"企业微信消息发送异常: {e}")


def get_test_summary(report_path):
    """从Allure报告中提取测试摘要信息"""
    try:
        summary_path = os.path.join(report_path, 'html', 'widgets', 'summary.json')
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('statistic', {})
        print(f"Allure摘要文件不存在: {summary_path}")
        return {}
    except Exception as e:
        print(f"获取测试统计信息失败: {e}")
        return {}



def job():
    """定时执行的任务函数（改为直接执行）"""
    print(f"[自动化测试] 开始执行测试: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        config = load_config()
        exit_code = run_tests(config)
        print(f"[自动化测试] 测试完成，退出码: {exit_code}")
    except Exception as e:
        print(f"[自动化测试] 执行异常: {e}")

if __name__ == "__main__":
    # 直接执行测试任务（无需定时循环）
    job()
    
