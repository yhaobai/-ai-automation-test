import pytest
from selenium import webdriver  #控制浏览器
from selenium.webdriver.chrome.service import Service  #需要通过这个类来指定 chromedriver 的路径,并配置相关的服务参数
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager  # 是一个方便的工具包，用于自动下载和管理不同浏览器驱动
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager  # 保留原有导入
from selenium.webdriver.chrome.options import Options  #Options 类用于设置 Chrome 浏览器的各种启动选项
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
import allure


@pytest.fixture(scope="function")  #函数级别
def browser(request):
    browser_name = request.config.getoption("--browser")
    headless = request.config.getoption("--headless")

    if browser_name == "chrome":
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    elif browser_name == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    elif browser_name == "edge":
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
    else:
        raise ValueError(f"浏览器{browser_name} 不支持")

    driver.implicitly_wait(10)
    yield driver
    driver.quit()


def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="store",
        default="edge",
        help="选择浏览器：chrome,firefox,edge"
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="无头模式运行"
    )