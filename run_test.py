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
import logging
import atexit

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_runner.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 全局变量存储服务器进程
server_process = None

def load_config():
    """加载配置文件，适配项目中config/config.ini的路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "config", "config.ini")
    if not os.path.exists(config_path):
        logging.error(f"配置文件 {config_path} 不存在，请检查路径是否正确")
        raise FileNotFoundError(f"配置文件 {config_path} 不存在，请检查路径是否正确")

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    return config

def find_free_port():
    """查找可用端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def is_port_available(host, port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def start_temp_server(report_html_path, config):
    """启动临时HTTP服务器并返回可访问的URL"""
    global server_process
    
    # 获取配置中的公网地址或域名
    public_address = config.get('server', 'public_address', fallback=None)
    
    # 如果没有配置公网地址，尝试获取本地IP
    if not public_address:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            public_address = s.getsockname()[0]
            s.close()
            logging.info(f"使用本地IP地址: {public_address}")
        except Exception as e:
            logging.error(f"无法获取本地IP地址: {e}")
            public_address = "localhost"
    
    # 查找可用端口
    port = find_free_port()
    max_retries = 5
    retries = 0
    
    # 尝试查找可用端口
    while not is_port_available(public_address, port) and retries < max_retries:
        logging.warning(f"端口 {port} 已被占用，尝试其他端口")
        port = find_free_port()
        retries += 1
    
    if retries >= max_retries:
        logging.error("无法找到可用端口")
        return None
    
    # 启动服务器
    cmd = f"python -m http.server {port} --directory {report_html_path} > server.log 2>&1 &"
    logging.info(f"启动临时服务器: {cmd}")
    
    try:
        server_process = subprocess.Popen(cmd, shell=True)
        
        # 等待服务器启动
        max_wait_time = 10  # 最大等待时间（秒）
        wait_interval = 0.5  # 检查间隔（秒）
        waited = 0
        
        while waited < max_wait_time:
            if is_port_available(public_address, port):
                # 如果端口仍可用，说明服务器可能未成功启动
                sleep(wait_interval)
                waited += wait_interval
            else:
                logging.info(f"服务器已在端口 {port} 上启动")
                break
        
        if waited >= max_wait_time:
            logging.warning("服务器启动超时，但继续尝试访问")
        
        # 返回可访问的链接
        return f"http://{public_address}:{port}/index.html"
    
    except Exception as e:
        logging.error(f"启动临时服务器失败: {e}")
        return None

def cleanup():
    """清理资源，关闭临时服务器"""
    global server_process
    if server_process:
        try:
            logging.info("关闭临时服务器")
            server_process.terminate()
            server_process.wait(timeout=5)
        except Exception as e:
            logging.error(f"关闭服务器失败: {e}")

def run_tests(config):
    """执行测试并生成报告"""
    # 创建报告目录
    report_dir = config.get('report', 'directory', fallback='reports')
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(report_dir, f'report_{timestamp}')
    os.makedirs(report_path, exist_ok=True)
    
    logging.info(f"开始执行测试，报告将生成到: {report_path}")

    # 执行测试
    pytest_args = [
        'tests/',
        '--alluredir', report_path,
        '-v',
        '-s'
    ]
    
    # 添加失败重试参数（如果配置中指定）
    if config.getboolean('pytest', 'reruns_enabled', fallback=False):
        reruns = config.getint('pytest', 'reruns', fallback=3)
        pytest_args.extend(['--reruns', str(reruns)])
    
    logging.info(f"执行 pytest 命令: pytest {' '.join(pytest_args)}")
    exit_code = pytest.main(pytest_args)
    logging.info(f"pytest 执行完成，退出码: {exit_code}")

    # 生成Allure报告
    allure_cmd = f'allure generate {report_path} -o {report_path}/html --clean --config allure.results.encoding=utf-8'
    logging.info(f"执行 Allure 报告生成命令: {allure_cmd}")
    
    result = subprocess.run(
        allure_cmd, 
        shell=True, 
        capture_output=True, 
        text=True
    )
    
    if result.returncode != 0:
        logging.error(f"Allure 报告生成失败: {result.stderr}")
        return exit_code
    else:
        logging.info(f"Allure 报告生成成功: {result.stdout}")

    # 生成在线访问链接
    report_html_path = os.path.join(report_path, 'html')
    
    # 检查报告文件是否存在
    if not os.path.exists(os.path.join(report_html_path, 'index.html')):
        logging.error(f"报告文件不存在: {report_html_path}/index.html")
        return exit_code
    
    report_url = start_temp_server(report_html_path, config)
    
    if not report_url:
        logging.error("无法获取有效的报告URL")
        report_url = "报告URL不可用，请检查服务器配置"

    logging.info(f"测试报告已生成: {report_url}")

    # 发送通知
    platform = config.get('notification', 'platform', fallback='dingtalk').lower()
    if platform == 'dingtalk':
        send_dingtalk_message(report_url, config, exit_code, report_path)
    elif platform == 'wechat':
        send_wechat_message(report_url, config, exit_code, report_path)
    else:
        logging.warning(f"不支持的通知平台: {platform}")

    return exit_code

def send_dingtalk_message(report_url, config, exit_code, report_path):
    """发送钉钉消息通知"""
    webhook_url = config.get('dingtalk', 'webhook')
    secret = config.get('dingtalk', 'secret', fallback=None)

    if not webhook_url:
        logging.error("钉钉Webhook未配置，无法发送通知")
        return

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
- **执行环境**: {socket.gethostname()}
- **执行结果**: {'✅ 全部通过' if exit_code == 0 else '❌ 存在失败'}
- **测试总数**: {test_summary.get('total', '未知')}
- **通过数量**: {test_summary.get('passed', '未知')}
- **失败数量**: {test_summary.get('failed', '未知')}
- **错误数量**: {test_summary.get('broken', '未知')}
- **跳过数量**: {test_summary.get('skipped', '未知')}
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
        try:
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
        except Exception as e:
            logging.error(f"生成钉钉签名失败: {e}")
            return

    try:
        logging.info(f"发送钉钉通知到: {webhook_url}")
        response = requests.post(webhook_url, headers=headers, data=json.dumps(message))
        response.raise_for_status()
        result = response.json()
        if result.get('errcode') == 0:
            logging.info("钉钉消息发送成功")
        else:
            logging.error(f"钉钉消息发送失败: {result.get('errmsg')}")
    except requests.RequestException as e:
        logging.error(f"钉钉消息发送异常: {e}")

def send_wechat_message(report_url, config, exit_code, report_path):
    """发送企业微信消息通知"""
    webhook_url = config.get('wechat', 'webhook')
    
    if not webhook_url:
        logging.error("企业微信Webhook未配置，无法发送通知")
        return

    test_summary = get_test_summary(report_path)

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""
# 📊 自动化测试报告
- **执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **执行环境**: {socket.gethostname()}
- **执行结果**: {'✅ 全部通过' if exit_code == 0 else '❌ 存在失败'}
- **测试总数**: {test_summary.get('total', '未知')}
- **通过数量**: {test_summary.get('passed', '未知')}
- **失败数量**: {test_summary.get('failed', '未知')}
- **错误数量**: {test_summary.get('broken', '未知')}
- **跳过数量**: {test_summary.get('skipped', '未知')}
- **查看详情**: [点击查看测试报告]({report_url})
"""
        }
    }

    try:
        logging.info(f"发送企业微信通知到: {webhook_url}")
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        result = response.json()
        if result.get('errcode') == 0:
            logging.info("企业微信消息发送成功")
        else:
            logging.error(f"企业微信消息发送失败: {result.get('errmsg')}")
    except requests.RequestException as e:
        logging.error(f"企业微信消息发送异常: {e}")

def get_test_summary(report_path):
    """从Allure报告中提取测试摘要信息"""
    try:
        # 优先尝试从报告目录获取摘要
        summary_path = os.path.join(report_path, 'html', 'widgets', 'summary.json')
        
        if not os.path.exists(summary_path):
            # 如果报告目录中没有，尝试从结果目录获取
            summary_path = os.path.join(report_path, 'widgets', 'summary.json')
        
        if os.path.exists(summary_path):
            logging.info(f"找到摘要文件: {summary_path}")
            with open(summary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('statistic', {})
        
        logging.warning(f"Allure摘要文件不存在: {summary_path}")
        
        # 如果摘要文件不存在，尝试从pytest结果中获取
        pytest_summary = get_pytest_summary(report_path)
        if pytest_summary:
            return pytest_summary
            
        return {}
    except Exception as e:
        logging.error(f"获取测试统计信息失败: {e}")
        return {}

def get_pytest_summary(report_path):
    """从pytest结果中提取测试摘要信息"""
    try:
        pytest_result_path = os.path.join(report_path, 'pytest_results.json')
        
        # 如果pytest结果文件不存在，尝试从stdout中获取
        if not os.path.exists(pytest_result_path):
            return None
            
        with open(pytest_result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 提取测试统计信息
            summary = {
                'total': data.get('summary', {}).get('total', '未知'),
                'passed': data.get('summary', {}).get('passed', '未知'),
                'failed': data.get('summary', {}).get('failed', '未知'),
                'broken': data.get('summary', {}).get('errors', '未知'),
                'skipped': data.get('summary', {}).get('skipped', '未知')
            }
            
            return summary
    except Exception as e:
        logging.error(f"获取pytest统计信息失败: {e}")
        return None

if __name__ == "__main__":
    # 注册清理函数
    atexit.register(cleanup)
    
    logging.info("===========================================")
    logging.info("开始执行自动化测试")
    logging.info("===========================================")
    
    try:
        config = load_config()
        exit_code = run_tests(config)
        logging.info(f"自动化测试完成，退出码: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logging.exception("执行测试时发生致命错误")
        sys.exit(1)
    finally:
        cleanup()
