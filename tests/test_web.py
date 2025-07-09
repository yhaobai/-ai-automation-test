import time
import pytest
from page.web_page import WebPage  #导入一些封装的定义的函数
import allure


@allure.feature("基本测试")
class TestBase:
    # @pytest.mark.skip
    @pytest.mark.parametrize("username, email, theme, message", [
        ("user001", "2312265316@qq.com", "欢迎访问系统", "838183")])
    def test_send_message(self,browser,username,email,theme,message):
        web_page = WebPage(browser)  #实例化
        web_page.open()  #调用
        web_page.screen_send()
        web_page.send_message(username,email, theme, message)


    def test_click_card(self,browser):
        web_page = WebPage(browser)
        web_page.open()
        web_page.screen_card()
        web_page.force_click(web_page.CLICK_CARD)








