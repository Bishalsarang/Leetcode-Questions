# Author: Bishal Sarang
import json
import os
import pickle
import time

import bs4
import colorama
import requests
from colorama import Back, Fore
from ebooklib import epub
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from utils import *
import epub_writer

# Initialize Colorama
colorama.init(autoreset=True)

options = Options()
options.headless = True
# Disable Warning, Error and Info logs
# Show only fatal errors
options.add_argument("--log-level=3")
driver = webdriver.Chrome(options=options)

# Get upto which problem it is already scraped from track.conf file
completed_upto = read_tracker("track.conf")

# Load chapters list that stores chapter info
# Store chapter info
with open('chapters.pickle', 'rb') as f:
    chapters = pickle.load(f)


def download(problem_num, url, title, solution_slug):
    print(
        Fore.BLACK + Back.CYAN + f"Fetching problem num " + Back.YELLOW + f" {problem_num} " + Back.CYAN + " with url " + Back.YELLOW + f" {url} ")
    n = len(title)

    try:

        driver.get(url)
        # Wait 20 secs or until div with id initial-loading disappears
        element = WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.ID, "initial-loading"))
        )
        # Get current tab page source
        html = driver.page_source
        soup = bs4.BeautifulSoup(html, "html.parser")

        # Construct HTML
        title_decorator = '*' * n
        problem_title_html = title_decorator + f'<div id="title">{title}</div>' + '\n' + title_decorator
        problem_html = problem_title_html + str(
            soup.find("div", {"class": "content__u3I1 question-content__JfgR"})) + '<br><br><hr><br>'

        # Append Contents to a HTML file
        with open("out.html", "ab") as f:
            f.write(problem_html.encode(encoding="utf-8"))

        # create and append chapters to construct an epub
        c = epub.EpubHtml(title=title, file_name=f'chap_{problem_num}.xhtml', lang='hr')
        c.content = problem_html
        chapters.append(c)

        # Write List of chapters to pickle file
        dump_chapters_to_file(chapters)
        # Update upto which the problem is downloaded
        update_tracker('track.conf', problem_num)
        print(
            Fore.BLACK + Back.GREEN + f"Writing problem num " + Back.YELLOW + f" {problem_num} " + Back.GREEN + " with url " + Back.YELLOW + f" {url} ")
        print(Fore.BLACK + Back.GREEN + " successfull ")
        # print(f"Writing problem num {problem_num} with url {url} successfull")

    except Exception as e:
        print(Back.RED + f" Failed Writing!!  {e} ")
        driver.quit()


def main():
    MAXIMUM_NUMBER_OF_PROBLEMS_PER_INSTANCE = int(os.environ.get("MAXIMUM_NUMBER_OF_PROBLEMS", 400))
    SLEEP_TIME_PER_PROBLEM_IN_SECOND = int(os.environ.get("SLEEP_TIME_PER_PROBLEM_IN_SECOND", 5))

    # Leetcode API URL to get json of problems on algorithms categories
    ALGORITHMS_ENDPOINT_URL = "https://leetcode.com/api/problems/algorithms/"

    # Problem URL is of format ALGORITHMS_BASE_URL + question__title_slug
    # If question__title_slug = "two-sum" then URL is https://leetcode.com/problems/two-sum
    ALGORITHMS_BASE_URL = "https://leetcode.com/problems/"

    # Load JSON from API
    algorithms_problems_json = requests.get(ALGORITHMS_ENDPOINT_URL).content
    algorithms_problems_json = json.loads(algorithms_problems_json)

    # List to store question_title_slug
    links = []
    for child in algorithms_problems_json["stat_status_pairs"]:
        # Only process free problems
        if not child["paid_only"]:
            question__title_slug = child["stat"]["question__title_slug"]
            question__article__slug = child["stat"]["question__article__slug"]
            question__title = child["stat"]["question__title"]
            frontend_question_id = child["stat"]["frontend_question_id"]
            difficulty = child["difficulty"]["level"]
            links.append(
                (question__title_slug, difficulty, frontend_question_id, question__title, question__article__slug))


    
    has_new_problems = (completed_upto != len(links) - 1)
    if has_new_problems:
        styles_str = "<style>pre{white-space:pre-wrap;background:#f7f9fa;padding:10px 15px;color:#263238;line-height:1.6;font-size:13px;border-radius:3px margin-top: 0;margin-bottom:1em;overflow:auto}b,strong{font-weight:bolder}#title{font-size:16px;color:#212121;font-weight:600;margin-bottom:10px}hr{height:10px;border:0;box-shadow:0 10px 10px -10px #8c8b8b inset}</style>"
        
        with open("out.html", "ab") as f:
            f.write(styles_str.encode(encoding="utf-8"))
    
    # Sort by difficulty follwed by problem id in ascending order
    links = sorted(links, key=lambda x: (x[1], x[2]))
    downloaded_now = 0
    try:
        for i in range(completed_upto + 1, len(links)):
            question__title_slug, _, frontend_question_id, question__title, question__article__slug = links[i]
            url = ALGORITHMS_BASE_URL + question__title_slug
            title = f"{frontend_question_id}. {question__title}"

            # Download each file as html and write chapter to chapters.pickle
            download(i, url, title, question__article__slug)
            downloaded_now += 1

            if downloaded_now == MAXIMUM_NUMBER_OF_PROBLEMS_PER_INSTANCE:
                break
            # Sleep for 5 secs for each problem and 2 mins after every 30 problems
            if i % 30 == 0:
                print(f"Sleeping 120 secs\n")
                time.sleep(120)
            else:
                print(f"Sleeping {SLEEP_TIME_PER_PROBLEM_IN_SECOND} secs\n")
                time.sleep(SLEEP_TIME_PER_PROBLEM_IN_SECOND)

    finally:
        # Close the browser after download
        driver.quit()

    try:
        if has_new_problems:
            epub_writer.write("Leetcode Questions.epub", "Leetcode Questions", "Anonymous", chapters)
            print(Back.GREEN + "All operations successful")
        else:
            print(Back.GREEN + "No new problems found. Exiting")
    except Exception as e:
        print(Back.RED + f"Error making epub {e}")


if __name__ == "__main__":
    main()
