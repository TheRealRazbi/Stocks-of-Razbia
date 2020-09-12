import ast
import sys
import time

from selenium import webdriver

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from queue import Queue
import _queue
from contextlib import suppress
from threading import Thread
import asyncio
import concurrent


class SeleniumController(Thread):
    def __init__(self):
        super().__init__()
        self.driver = None
        self.on_streamlabs_page = False
        self.setup()
        self.tabs_used = 2
        self.tab_location = 0
        self._queue = Queue()
        self.pool_frequency = 0.1

    def setup(self):
        options = Options()
        options.binary_location = "C:/Program Files (x86)/BraveSoftware/Brave-Browser/Application/brave.exe"
        driver_path = "C:/Users/Calculator/PycharmProjects/StocksMinigame/lib/selenium stuff/chromedriver.exe"
        options.add_argument("user-data-dir=C:/Users/Calculator/PycharmProjects/StocksMinigame/lib/selenium stuff/cookies")
        self.driver = webdriver.Chrome(executable_path=driver_path, options=options)

    def ready_check(self):
        if not self.on_streamlabs_page:
            self.driver.get("https://streamlabs.com/dashboard#/cloudbot/loyalty/users")
            self.on_streamlabs_page = True

    def get_table_text(self):
        self.ready_check()

        return self.wait_for_element_css_selector('[platform=twitch] table').text.split("\n")[1:]

    def search_user(self, user: str):
        self.ready_check()
        while True:
            try:
                search_bar = self.wait_for_element_css_selector('[platform=twitch] input')
            except TimeoutException:
                # self.search_user(user)
                pass
            else:
                break
        # self.driver.execute_script(f"arguments[0].value='{user[:-1]}';", search_bar)
        # search_bar.send_keys(user[-1])
        # self.driver.execute_script(f"arguments[0].value='';", search_bar)
        search_bar.clear()
        search_bar.send_keys(user)

    def wait_for_element_css_selector(self, css_selector):
        return WebDriverWait(self.driver, 10, poll_frequency=self.pool_frequency).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))

    def get_points(self, user: str):
        self.search_user(user=user)
        start_timer = time.time()
        while self.get_table_text()[0].split(' ')[0] != user:
            time.sleep(0.01)
        points = self.get_table_text()[0].split(' ')[1]
        print(f"{round(time.time()-start_timer, 4)} seconds to find {user} and they have {points} points")
        return points

    def find_button(self, button_name: str):
        WebDriverWait(self.driver, 10, poll_frequency=self.pool_frequency).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[platform=twitch] button')))
        buttons = self.driver.find_elements_by_css_selector('[platform=twitch] button')
        while len(buttons) < 4:
            buttons = self.driver.find_elements_by_css_selector('[platform=twitch] button')
        for button in buttons:
            if button.text.lower() == button_name.lower():
                # print(f"FOUND button {button_name}")
                return button

    def find_user_in_current_table(self, user: str):
        current_table = self.get_table_text()
        for group in current_table:
            group = group.split(' ')
            if group[0] == user:
                # print(f"Found {user}")
                return group
        # print(f"Couldn't find user {user} in {current_table}")

    def wait_for_next_page(self, button_element, backwards=False):
        current_page = self.get_current_page()
        button_element.click()
        WebDriverWait(self.driver, 10, poll_frequency=self.pool_frequency).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '[platform=twitch] span'),
                                                                              f'Page {current_page-1 if backwards else current_page+1}'))

    def get_current_page(self):
        return int(self.wait_for_element_css_selector('[platform=twitch] span').text.split(' ')[1])

    def get_points_in_pages(self, user: str):
        self.ready_check()
        start_timer = time.time()
        previous_button = self.find_button('previous')
        while not previous_button.get_attribute('disabled'):
            self.wait_for_next_page(previous_button, backwards=True)

        found = None
        next_button = self.find_button('next')
        while found is None:
            found = self.find_user_in_current_table(user=user)
            if found:
                print(f"{round(time.time() - start_timer, 4)} seconds to find {user} and they have {found[1]} points")
                return found
            if next_button.get_attribute('disabled'):
                break
            self.wait_for_next_page(next_button)

    def create_new_tab(self):
        self.driver.execute_script("window.open('https://streamlabs.com/dashboard#/cloudbot/loyalty/users','_blank');")

    def setup_n_tabs(self):
        self.driver.get("https://streamlabs.com/dashboard#/cloudbot/loyalty/users")
        if len(self.driver.window_handles) <= self.tabs_used-1:
            needed = self.tabs_used-len(self.driver.window_handles)
            for i in range(needed):
                self.create_new_tab()
        self.on_streamlabs_page = True

    def switch_to_tab(self, tab_location: int):
        self.driver.switch_to.window(self.driver.window_handles[tab_location])
        self.tab_location = tab_location

    def get_points_using_multiple_tabs(self, groups):
        if not self.on_streamlabs_page:
            self.setup_n_tabs()
            time.sleep(0.5)
        # self.setup_n_tabs()
        # self.prepare_pages()
        start_timer = time.time()

        self.queue_users(groups)
        self.finish_searching_users(groups)

        print(f"{round(time.time() - start_timer, 4)} seconds to find {len(groups)} user{'s' if len(groups) > 1 else ''}.")

        # self.prepare_pages()

    def queue_users(self, groups):
        # print(list(zip(range(2), groups)))
        for (tab, (command, args, future)) in zip(range(self.tabs_used), groups):
            self.switch_to_tab(tab)
            self.search_user(args[0])

    def finish_searching_users(self, groups):
        for (tab, (command, args, future)) in zip(range(self.tabs_used), groups):
            user = args[0]
            self.switch_to_tab(tab)
            while True:
                try:
                    WebDriverWait(self.driver, 5, poll_frequency=self.pool_frequency).until(
                        EC.text_to_be_present_in_element((By.CSS_SELECTOR, '[platform=twitch] table'),
                                                         user))
                except TimeoutException:
                    self.search_user(user)
                else:
                    break

            data = self.get_table_text()[0].split(' ')

            if command == '!get_user_points':
                future.set_result(data[1])
            elif '!add_points' == command:
                s.driver.find_element_by_css_selector('[platform=twitch] i.icon-edit').click()
                points_field = self.driver.find_element_by_css_selector('[platform=twitch] input[name=points]')
                points = int(points_field.get_attribute('value'))
                self.driver.execute_script(f"arguments[0].value='';", points_field)
                points_field.send_keys(str(points+args[1]))
                print(points_field.get_attribute('value'))
                save_button = self.find_button('save')
                time.sleep(0.1)
                save_button.click()
                future.set_result("done")

    async def task(self, command, *args):
        future = concurrent.futures.Future()
        self._queue.put((command, args, future))
        return await asyncio.futures.wrap_future(future)

    def run(self):
        while True:
            groups = [self._queue.get()]
            time.sleep(.05)
            with suppress(_queue.Empty):
                for _ in range(self.tabs_used-1):
                    groups.append(self._queue.get(block=False))

            self.get_points_using_multiple_tabs(groups)

            # if next_.get_attribute('disabled'):
            #     continue


if __name__ == '__main__':
    # sys.path.append('C:\\Users\\Calculator\\PycharmProjects\\StocksMinigame\\')
    s = SeleniumController()
    # with open('../lib/selenium stuff/cookies.txt', 'r') as f:
    # with open('../lib/selenium stuff/cookies.txt', 'r') as f:
    #     cookies = ast.literal_eval(f.read())
    # for cookie in cookies:
    #     print(cookie)
    #     driver.add_cookie(cookie)
    # input()
    # input()
    # s.driver.get("https://streamlabs.com/dashboard#/cloudbot/loyalty/users")
    # users = s.driver.find_element_by_css_selector('[platform=twitch] table').text.split("\n")[1:]
    # input(users)
    # s.get_points('razbith3player')
    # s.get_points('alexvidinei')
    # s.get_points('genassassin200')
    # s.get_points('danylalex')
    # s.get_points('razbith3smurf')
    # s.get_points('chewmule')

    async def find_some_stuff(selenium_controller):
        tab = 1
        selenium_controller.tabs_used = tab
        test_subjects = ['razbith3player', 'danylalex', 'genassassin200', 'alexvidinei', 'chewmule', 'congnato',
                         'canadianwolverine', 'aygabriel', 'fastine', 'grom4er', 'florin9895', 'gremtan1', 'xflorin97',
                         'zevolf', 'souleater780', 'doctorul_', 'hetudor', 'himekoelectric']
        # await asyncio.gather(*[selenium_controller.task('!get_user_points', user) for user in test_subjects[:selenium_controller.tabs_used:-1]])
        # print("\nThis test is just to boot it^")
        timer_start = time.time()
        # await asyncio.gather(*[selenium_controller.task('!get_user_points', user) for user in test_subjects])
        await asyncio.gather(selenium_controller.task('!add_points', 'davari02', 5))

        print(f"\n{round(time.time() - timer_start, 4)} seconds to find all {len(test_subjects)} in total by using {tab} tabs")


    try:
        s.start()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(find_some_stuff(s))
        # starter_timer = time.time()
        # # s.get_points_in_pages_using_2_tabs('congnato')
        # # s.get_points_in_pages_using_2_tabs('razbith3player')
        # # s.get_points_in_pages_using_2_tabs('alexvidinei')
        # # s.get_points_in_pages_using_2_tabs('danylalex')
        # s.get_points('congnato')
        # s.get_points('razbith3player')
        # s.get_points('alexvidinei')
        # s.get_points('danylalex')
        # print(f"{round(time.time() - starter_timer, 4)} seconds to find all 4 in total.")
        #
        # # s.get_points_in_pages('congnato')
        # # s.get_points_in_pages('razbith3player')
        # # s.get_points_in_pages('alexvidinei')
        # # s.get_points_in_pages('danylalex')
        # # # print(s.get_table_text())
        # input()
        # s.driver.close()
        # print(driver.get_cookies())
    finally:
        s.driver.close()


