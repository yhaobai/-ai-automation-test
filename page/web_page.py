from selenium.webdriver.common.by import By
from page.base_page import BasePage
import allure
import os
import time

class WebPage(BasePage):
    #  定位器
    USERNAME_INPUT = (By.ID,"name")
    EMAIL_INPUT = (By.ID,"email")
    THEME_INPUT = (By.ID,"subject")
    MESSAGE_INPUT = (By.ID,"message")
    PASSWORD_INPUT = (By.ID,"password")
    CLICK_BOTT = (By.XPATH, "//section[@id='contact']//button[@class='btn-primary' and @type='submit']")
    CLICK_CARD = (By.XPATH, '''
        //button[
            @onclick="showDetail('即时导航', 'instant-navigation')" and 
            contains(@class, 'text-primary')
        ]
    ''')

    def __init__(self,driver):
        super().__init__(driver)
        # 动态拼接本地文件路径（跨平台兼容）
        local_path = os.path.abspath(r"D:\ui_test\index.html")
        # 转换为 file:// 协议的 URL（自动处理路径分隔符）
        self.url = f"file://{local_path.replace(os.sep,'/')}"

    def open(self):
        with allure.step(f"打开页面：{self.url}"):
            self.driver.get(self.url)

    def send_message(self,username,email,theme,message):
        self.send_keys(self.USERNAME_INPUT,username)
        self.send_keys(self.EMAIL_INPUT,email)
        self.send_keys(self.THEME_INPUT,theme)
        self.send_keys(self.MESSAGE_INPUT,message)
        self.click(self.CLICK_BOTT)

    def card_click(self):
        self.click(self.CLICK_CARD)

    def screen_send(self):
        self.scroll_to_element(self.USERNAME_INPUT)

    def screen_card(self):
        self.scroll_to_element(self.CLICK_CARD)

    def force_click(self, locator):
        """
        强制点击指定元素，处理元素被遮挡的情况
        :param locator: 元素定位器，如 ("id", "element_id")
        """
        with allure.step(f"强制点击元素: {locator}"):
            element = self.find_element(locator)
            # 检查元素是否被遮挡
            is_obstructed = self.driver.execute_script("""
                const elem = arguments[0];
                const rect = elem.getBoundingClientRect();
                return document.elementFromPoint(rect.left + rect.width/2, rect.top + rect.height/2) !== elem;
            """, element)

            if is_obstructed:
                print("元素被遮挡，尝试滚动到元素并使用 JS 点击")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)  # 等待滚动完成
                self.driver.execute_script("arguments[0].click();", element)
            else:
                print("元素未被遮挡，使用常规点击")
                element.click()