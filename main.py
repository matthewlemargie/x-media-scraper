from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import sys
import os
import subprocess
import time
from tqdm import tqdm
import json
import argparse

parser = argparse.ArgumentParser(description="XMediaScraper")
parser.add_argument("--skip-gifs", action="store_true", help="Don't download gifs from profiles'")
parser.add_argument("--multiple-accounts", action="store_true", help="Don't download gifs from profiles'")

args = parser.parse_args()

video_types = set(["mp4", "m4v", "avi", "mkv"])

def return_file_set_from_directory(directory_path):
    res = set()
    if os.path.exists(directory_path):
        for file in os.listdir(directory_path):
            if os.path.isfile(os.path.join(directory_path, file)):
                if file.split(".")[-1] in video_types:
                    isVideo = True
                else:
                    isVideo = False
                res.add((file.split("_")[0], isVideo))
    return res

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

def select_media_tab(webDriver):
    # select media tab on profile
    while True:
        elements = webDriver.find_elements(By.CSS_SELECTOR, "a.css-175oi2r.r-1awozwy.r-6koalj.r-eqz5dr.r-16y2uox.r-1h3ijdo.r-1777fci.r-s8bhmr.r-1c4vpko.r-1c7gwzm.r-o7ynqc.r-6416eg.r-1ny4l3l.r-1loqt21")
        if len(elements) >= 3:
            break
        time.sleep(1)
    elements[-1].click()

def check_content_loaded(webDriver):
    images_found = False
    max_attempts = 3
    attempts = 0
    # make sure content has loaded
    while attempts < max_attempts:
        soup = BeautifulSoup(webDriver.page_source, 'html.parser')
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
    return images_found


def get_content_urls(webDriver):
    urls = set()
    # get urls for every piece of content
    while True:
        urls_len = len(urls)

        while True:
            soup = BeautifulSoup(webDriver.page_source, 'html.parser')
            section = soup.find("section", class_="css-175oi2r")
            try:
                links = section.find_all("a")
                if links is not None:
                    break
            except:
                continue

        for link in links:
            href = link.get("href")
            if (href,) in urls:
                continue
            try:
                isGif = link.find("span", class_="css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3").text == "GIF"
            except:
                isGif = False
            
            urls.update([(href, isGif)])

        if len(urls) == urls_len:
            break

        # Scroll to the bottom of the page
        webDriver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(1)

    return tuple(urls)

def download_media_from_urls(urls, accountdir):
    isVideo = False
    for i in tqdm(range(len(urls))):
        id = urls[i][0].split("/")[-3]
        media_type = urls[i][0].split("/")[-2]
        if args.skip_gifs and urls[i][1]:
            continue
        if media_type == "video" or urls[i][1]:
            isVideo = True
        else:
            isVideo = False
        if (id, isVideo) not in done_set:
            subprocess.run([
                "gallery-dl", 
                "--quiet", 
                "--cookies", 
                "cookies.txt", 
                f"{sitebase + urls[i][0]}", 
                "--directory", 
                accountdir + "/"
            ])
            time.sleep(2)

def launch_x_webdriver():
    driver = webdriver.Firefox()
    driver.get("https://x.com")
    import_cookies(driver, "cookies.txt")
    return driver

def switch_account(webDriver, accounts_visited):
    while True:
        button = driver.find_element(By.CSS_SELECTOR, "button.css-175oi2r.r-1awozwy.r-sdzlij.r-6koalj.r-18u37iz.r-xyw6el.r-1loqt21.r-o7ynqc.r-6416eg.r-1ny4l3l")
        button.click()
        time.sleep(2)
        try:
            div = driver.find_element(By.CSS_SELECTOR, "div.css-175oi2r.r-1azx6h.r-7mdpej.r-1vsu8ta.r-ek4qxl.r-1dqxon3.r-1ipicw7")
            accounts = div.find_elements(By.CSS_SELECTOR, "button.css-175oi2r.r-1mmae3n.r-3pj75a.r-1loqt21.r-o7ynqc.r-6416eg.r-1ny4l3l")
            for acc in accounts:
                account = acc.find_element(By.CSS_SELECTOR, "span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3").text
                if account not in accounts_visited:
                    acc.click()
                    accounts_visited.add(acc)
                    break
            accounts_visited = set()
            accounts[0].click()
            break
        except:
            webDriver.refresh()
            continue

sitebase = "https://x.com"
imgdir = '/home/dmac/Pictures/'

accountfile = open("accounts.info", "r")
accounts = accountfile.readlines()
accountfile.close()

try:
    driver = launch_x_webdriver()

    for account_url in accounts:
        account_name = account_url.split("/")[-1]
        accountdir = os.path.join(imgdir, account_name).strip() + "/"
        done_set = return_file_set_from_directory(accountdir)

        accounts_visited = set()
        i = 0
        limit = 3
        while True:
            if i % limit == 0 and i > 0:
                switch_account(driver, accounts_visited) if args.multiple_accounts else (driver.close(), sys.exit(0))
            
            driver.get(account_url)
            select_media_tab(driver)
            time.sleep(2)
            
            content_loaded = check_content_loaded(driver)
            if content_loaded:
                break
            
            i += 1

        urls = get_content_urls(driver)
        download_media_from_urls(urls, accountdir)

    driver.close()
except KeyboardInterrupt:
    pass
