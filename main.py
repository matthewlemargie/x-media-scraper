from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import os
import time
from yt_dlp import YoutubeDL

loginfile = open("login.info", "r")
username = loginfile.readline() 
password = loginfile.readline() 
loginfile.close()

accountfile = open("accounts.info", "r")
accounts = accountfile.readlines()
accountfile.close()

imgdir = '/home/dmac/Pictures/'

driver = webdriver.Firefox()
cookies = driver.get_cookies()

driver.get("https://x.com")

time.sleep(4)
driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/main/div/div/div[1]/div/div/div[3]/div[4]/a').click()
# username
time.sleep(4)
driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[4]/label/div/div[2]/div/input').send_keys(username)
driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]/div').click()

# password
time.sleep(4)
driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input').send_keys(password)
driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button').click()
time.sleep(4)

for cookie in cookies:
    driver.add_cookie(cookie)

for account_url in accounts:
    account_name = account_url.split("/")[-1]
    driver.get(account_url)
    time.sleep(4)
    driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/div[2]/nav/div/div[2]/div/div[3]/a').click()

    time.sleep(4)
    img_urls = set()

    while True:
        urls_len = len(img_urls)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        images = soup.find_all("img", class_="css-9pa8cd")

        new_urls = {img.get("src") for img in images if img.get("src")}
        img_urls.update(new_urls)

        if len(img_urls) == urls_len:
            break

        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        try:
            WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "css-9pa8cd"))
                    )
        except TimeoutException:
            print("Timed out waiting for images to load.")

        # Sleep to avoid overwhelming the server with requests
        time.sleep(2)

    accountdir = os.path.join(imgdir, account_name)
    os.makedirs(accountdir, exist_ok=True)

    for url in img_urls:
        img = requests.get(url)
        file_path = os.path.join(accountdir, url.split('/')[-1])
        with open(file_path, 'wb') as f:
            f.write(img.content)

driver.close()
