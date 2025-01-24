from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import os
import subprocess
import time
from tqdm import tqdm
import json

def return_file_set_from_directory(directory_path):
    if os.path.exists(directory_path):
        return {file.split("_")[0] for file in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, file))}
    else:
        return set()

def truncate_title(title, max_length=50):
    return title[:max_length] if len(title) > max_length else title

def import_cookies(driver, file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("#") or not line.strip():
                continue
            
            fields = line.strip().split("\t")
            if len(fields) != 7:
                continue
            
            cookie = {
                "domain": fields[0],
                "httpOnly": fields[3].lower() == "true",
                "path": fields[2],
                "secure": fields[3].lower() == "true",
                "expiry": int(fields[4]) if fields[4].isdigit() else None,
                "name": fields[5],
                "value": fields[6],
            }
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Failed to add cookie: {cookie}, error: {e}")

sitebase = "https://x.com"
imgdir = '/home/dmac/Pictures/'

driver = webdriver.Firefox()
driver.get(sitebase)
import_cookies(driver, "cookies.txt")

accountfile = open("accounts.info", "r")
accounts = accountfile.readlines()
accountfile.close()

try:
    for account_url in accounts:
        account_name = account_url.split("/")[-1]
        while True:
            driver.get(account_url)

            while True:
                elements = driver.find_elements(By.CSS_SELECTOR, "a.css-175oi2r.r-1awozwy.r-6koalj.r-eqz5dr.r-16y2uox.r-1h3ijdo.r-1777fci.r-s8bhmr.r-1c4vpko.r-1c7gwzm.r-o7ynqc.r-6416eg.r-1ny4l3l.r-1loqt21")
                if len(elements) >= 3:
                    break
                time.sleep(1)
            try:
                elements[-1].click()
            except IndexError:
                continue

            time.sleep(2)
            images_found = False
            max_attempts = 3
            attempts = 0

            while attempts < max_attempts:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                section = soup.find("section", class_="css-175oi2r")

                if section:
                    try:
                        images = section.find_all("img")
                        if images:
                            images_found = True
                            break
                    except Exception as e:
                        pass

                attempts += 1
                time.sleep(1)

            if images_found:
                break
            else:
                continue

        urls = set()

        while True:
            urls_len = len(urls)

            while True:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                section = soup.find("section", class_="css-175oi2r")
                try:
                    links = section.find_all("a")
                    if links is not None:
                        break
                except:
                    continue

            links = {link.get("href") for link in links if link.get("href")}

            urls.update(links)

            if len(urls) == urls_len:
                break

            # Scroll to the bottom of the page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            time.sleep(1)

        accountdir = os.path.join(imgdir, account_name)
        accountdir = accountdir.strip() + "/"
        done_set = return_file_set_from_directory(accountdir)

        urls = list(urls)

        for i in tqdm(range(len(urls))):
            id = urls[i].split("/")[-3]
            if id not in done_set:
                subprocess.run([
                    "gallery-dl", 
                    "--quiet", 
                    "--cookies", 
                    "cookies.txt", 
                    f"{sitebase + urls[i]}", 
                    "--directory", 
                    accountdir + "/"
                ])
                time.sleep(4)

    driver.close()
except KeyboardInterrupt:
    pass
