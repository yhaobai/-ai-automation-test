from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import allure


class BasePage:
    def __init__(self,driver):
        self.driver = driver
        self.timeout = 20


    def find_element(self,locator):
        return WebDriverWait(self.driver,self.timeout).until(
            EC.presence_of_element_located(locator),message=f"找不到元素：{locator}"
        )

    def click(self,locator):
        with allure.step(f"点击元素：{locator}"):
            element =  WebDriverWait(self.driver,self.timeout).until(
                EC.element_to_be_clickable(locator)
            )
            element.click()

    def send_keys(self,locator,text):
        with allure.step(f"输入文本：{text} 到元素：{locator}"):
            element = self.find_element(locator)
            element.clear()
            element.send_keys(text)

    def get_title(self):
        return self.driver.title

    def scroll_screen(self, direction="down", pixels=300):
        """
        滚动页面指定方向和距离

        参数:
            direction: 滚动方向，可选值: "down"、"up"、"right"、"left"
            pixels: 滚动的像素值
        """
        with allure.step(f"向{direction}滚动{pixels}像素"):
            if direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {pixels});")
            elif direction == "up":
                self.driver.execute_script(f"window.scrollBy(0, -{pixels});")
            elif direction == "right":
                self.driver.execute_script(f"window.scrollBy({pixels}, 0);")
            elif direction == "left":
                self.driver.execute_script(f"window.scrollBy(-{pixels}, 0);")
            else:
                raise ValueError(f"不支持的滚动方向: {direction}")
            self.driver.implicitly_wait(1)  # 等待页面加载

    def scroll_to_element(self, locator):
        """
        滚动到指定元素位置

        参数:
            locator: 元素定位器，如 ("id", "element_id")
        """
        with allure.step(f"滚动到元素: {locator}"):
            element = self.find_element(locator)
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            self.driver.implicitly_wait(1)  # 等待页面加载


    def take_screenshot(self,name = "screenshot"):
        with allure.step(f"截图：{name}"):
            allure.attach(
                self.driver.get_screenshot_as_png(),
                name=name,
                attachment_type=allure.attachment_type.PNG
            )








