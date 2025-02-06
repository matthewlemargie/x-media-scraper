from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import sys
import os
import subprocess
import multiprocessing
import time
from tqdm import tqdm
from datetime import datetime
import json
from glob import glob
import argparse

parser = argparse.ArgumentParser(description="XMediaScraper")
parser.add_argument("--skip-gifs", action="store_true", help="Don't download gifs from profiles")
parser.add_argument("--multiple-accounts", action="store_true", help="Cycle through x accounts when rate limit hits")
parser.add_argument("--limit", type=int, default=2, help="Number of times to check for media before switching accounts")
parser.add_argument("--out-dir", type=str, default="/home/dmac/Pictures/", help="Directory where media will be saved")
parser.add_argument("--time-limit", type=int, default=120, help="How long to wait before switching accounts due to rate limit")

args = parser.parse_args()

video_types = set(["mp4", "m4v", "avi", "mkv"])

site = "https://x.com"

cookie_files = glob(f"{os.getcwd()}/*cookies*.txt")

def _import_cookies(driver, filePath):
    with open(filePath, 'r') as file:
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

def launch_webdriver(website):
    driver = webdriver.Firefox()
    driver.get(website)
    _import_cookies(driver, "cookies1.txt")
    return driver

def return_file_set_from_directory(path):
    res = set()
    if os.path.exists(path):
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)):
                if file.split(".")[-1] in video_types:
                    isVideo = True
                else:
                    isVideo = False
                res.add((file.split("_")[0], isVideo))
    return res

def switch_account(webDriver, accountsVisited):
    while True:
        button = webDriver.find_element(By.CSS_SELECTOR, "button.css-175oi2r.r-1awozwy.r-sdzlij.r-6koalj.r-18u37iz.r-xyw6el.r-1loqt21.r-o7ynqc.r-6416eg.r-1ny4l3l")
        button.click()
        try:
            div = webDriver.find_element(By.CSS_SELECTOR, "div.css-175oi2r.r-1azx6h.r-7mdpej.r-1vsu8ta.r-ek4qxl.r-1dqxon3.r-1ipicw7")
            accounts = div.find_elements(By.CSS_SELECTOR, "button.css-175oi2r.r-1mmae3n.r-3pj75a.r-1loqt21.r-o7ynqc.r-6416eg.r-1ny4l3l")
            for acc in accounts:
                account = acc.find_elements(By.CSS_SELECTOR, "span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3")[0].text
                if account not in accountsVisited:
                    acc.click()
                    accountsVisited.add(account)
                    time.sleep(2)
                    return
            accountsVisited = set()
            accounts[0].click()
            return
        except:
            pass

def select_media_tab(webDriver):
    # select media tab on profile
    while True:
        elements = webDriver.find_elements(By.CSS_SELECTOR, "a.css-175oi2r.r-1awozwy.r-6koalj.r-eqz5dr.r-16y2uox.r-1h3ijdo.r-1777fci.r-s8bhmr.r-3pj75a.r-o7ynqc.r-6416eg.r-1ny4l3l.r-1loqt21")
        if len(elements) >= 3:
            break
        time.sleep(1)
    elements[-1].click()

def check_content_loaded(webDriver):
    # make sure content has loaded
    images_found = False
    max_attempts = 3
    attempts = 0
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

def download_media_from_urls(urls, accountName, accountDir, doneSet, cache, cookieNum):
    isVideo = False
    rate_limited = False
    old_post = False
    first_date = None
    for i in tqdm(range(len(urls))):
        id = urls[i][0].split("/")[-3]
        media_type = urls[i][0].split("/")[-2]
        if args.skip_gifs and urls[i][1]:
            continue
        isVideo = media_type == "video" or urls[i][1]
        if (id, isVideo) not in doneSet:
            while True:
                try:
                    subprocess.run([
                        "gallery-dl",
                        "--quiet",
                        "--write-metadata",
                        "--cookies", cookie_files[cookieNum],
                        f"{site}{urls[i][0]}",
                        "--directory", f"{accountDir}{os.sep}"
                    ], timeout=args.time_limit)
                    break
                except:
                    cookieNum = (cookieNum + 1) % len(cookie_files)
                    cookies = cookie_files[cookieNum]
            old_post, date = _is_in_download_cache(cache, accountName, accountDir)
            if old_post:
                break
            if first_date is None:
                first_date = date
            time.sleep(2)
    if first_date != None:
        cache[accountName] = first_date

home_directory = os.path.expanduser("~")
cache_file = os.path.join(home_directory, ".x_media_downloader_cache")

def load_download_cache():
    cache = dict()
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            for line in f:
                account, date = line.split(" ", 1)
                account = account + "\n"
                cache[account] = datetime.fromisoformat(date.strip())
    return cache

def _is_in_download_cache(cache, accountName, accountDir):
    jsonfiles = glob(f"{accountDir}{os.sep}{"*.json"}")
    with open(jsonfiles[0], "r") as file:
        metadata = json.load(file)
    post_date = metadata.get("date")
    post_date = datetime.fromisoformat(post_date)
    os.remove(jsonfiles[0])
    if cache[accountName] >= post_date:
        return True, post_date
    else:
        return False, post_date

def write_download_cache(cache):
    with open(cache_file, "w") as f:
        for k, v in cache.items():
            f.write(f"{k.strip()} {v}\n")

def main():
    cookie_num = 0
    imgdir = args.out_dir

    accountfile = open("accounts.info", "r")
    accounts = accountfile.readlines()
    accountfile.close()

    cache = load_download_cache()
    for account_url in accounts:
        account_name = account_url.split("/")[-1]
        if account_name not in cache:
            cache[account_name] = datetime(2000, 1, 1, 0, 0, 0)

    try:
        driver = launch_webdriver(site)

        for account_url in accounts:
            account_name = account_url.split("/")[-1]
            account_dir = os.sep
            dirs = imgdir.split(os.sep)
            for d in dirs:
                account_dir = os.path.join(account_dir, d)
            account_dir = os.path.join(account_dir ,account_name).strip()

            accounts_visited = set()
            done_set = return_file_set_from_directory(account_dir)
            i = 0
            while True:
                if i % args.limit == 0 and i > 0:
                    if args.multiple_accounts:
                        switch_account(driver, accounts_visited)
                        cookie_num += 1
                    else:
                        driver.close()
                        sys.exit(0)
                driver.get(account_url)
                select_media_tab(driver)
                if check_content_loaded(driver):
                    break
                i += 1
            urls = get_content_urls(driver)
            download_media_from_urls(urls, account_name, account_dir, done_set, cache, cookie_num)
            os.system(f"rm {account_dir}{os.sep}*.json")

            write_download_cache(cache)

        driver.close()
    except KeyboardInterrupt:
        pass

main()
