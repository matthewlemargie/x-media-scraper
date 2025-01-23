from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import requests
import os
import subprocess
import time
from yt_dlp import YoutubeDL
import json

def truncate_title(title, max_length=50):
    return title[:max_length] if len(title) > max_length else title

def import_cookies(driver, file_path):
    with open(file_path, 'r') as file:
        for line in file:
            # Skip comments and blank lines
            if line.startswith("#") or not line.strip():
                continue
            
            # Split cookie attributes based on tab separation
            fields = line.strip().split("\t")
            if len(fields) != 7:
                continue  # Ensure the correct format
            
            # Map fields to Selenium cookie structure
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
        driver.get(account_url)
        while True:
            elements = driver.find_elements(By.CSS_SELECTOR, "a.css-175oi2r.r-1awozwy.r-6koalj.r-eqz5dr.r-16y2uox.r-1h3ijdo.r-1777fci.r-s8bhmr.r-1c4vpko.r-1c7gwzm.r-o7ynqc.r-6416eg.r-1ny4l3l.r-1loqt21")
            if len(elements) < 3:
                continue
            else:
                break
        elements[-1].click()

        time.sleep(1)
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

        for url in urls:
            if "photo" in url:
                subprocess.run([
                    "gallery-dl", 
                    "--cookies", 
                    "cookies.txt", 
                    f"{sitebase + url}", 
                    "--directory", 
                    accountdir + "/"
                ])
            time.sleep(1)

        for url in urls:
            if "video" in url:
                os.system(f"yt-dlp \"{sitebase + url}\" -o \"{accountdir.strip()}/%(title).50s_%(playlist_index)s.%(ext)s\" --cookies-from-browser firefox")
            time.sleep(1)

    driver.close()
except KeyboardInterrupt:
    pass
