import time
from urllib.parse import urldefrag
import os
import errno
import requests
import argparse
from bs4 import BeautifulSoup

exclude_strings = ["contest_banner", "archived", "closed", "sticky", "modicon", "adminicon"]
media_formats = [".jpg", ".png", ".gif", ".webm"]

def get_threads_from_board(url):
    pages = list()
    pages.append(url)
    for i in range(2, 11):
        pages.append(url + str(i))

    threads = list()

    for page in pages:
        response = requests.get(page)
        soup = BeautifulSoup(response.text, "lxml")
        for link in soup.find_all("span", class_="postNum"):
            link = link.a
            pure_url, frag = urldefrag(link.get("href"))
            thread = url + pure_url
            threads.append(thread)

    print("Found the following " + str(len(threads)) + " threads:")
    for thread in threads:
        print(thread)

    return threads


def get_threads_from_archive(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")

    threads = list()

    for link in soup.find(id="arc-list").find_all("a"):
        thread = "https://boards.4chan.org" + str(link.get("href"))
        threads.append(thread)

    print("Found the following " + str(len(threads)) + " threads:")
    for thread in threads:
        print(thread)

    return threads


def get_images_in_thread(url, small):
    html_page = requests.get(url).text
    soup = BeautifulSoup(html_page, "lxml")

    images = list()

    if small:
        for image in soup.find_all("img"):
            src = "https:" + image.get("src")
            if any(string in src for string in exclude_strings):
                continue
            if any(format in src for format in media_formats):
                print("Found image " + src)
                images.append(src)
    else:
        for image in soup.find_all("a", class_="fileThumb"):
            src = "https:" + image.get("href")
            if any(string in src for string in exclude_strings):
                continue
            if any(format in src for format in media_formats):
                print("Found image " + src)
                images.append(src)

    return images


def download_images(images, dir_name):
    if not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name)
        except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    number_of_downloads = 0
    for image in images:
        print("Downloading image " + image)
        image_data = requests.get(image).content

        file_name = image.split("/")[-1]
        file_path = os.path.join(dir_name, file_name)

        print("Writing image to " + file_path)
        f = open(file_path, "wb")
        f.write(image_data)
        f.close()
        number_of_downloads = number_of_downloads + 1

    return number_of_downloads


if __name__ == "__main__":
    start_time = time.time()

    out_dir = os.getcwd()

    parser = argparse.ArgumentParser(description="4chan image crawler - download all images from a board or a thread")

    parser.add_argument("board", help="board to download the images from")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-a", "--archive", help="download images from all threads in the archive", action="store_true")
    group.add_argument("-t", "--thread", help="replace the board with a link to a specific thread", action="store_true")

    parser.add_argument("-d", "--directory", help="save files to special directory", default=out_dir)
    parser.add_argument("-s", "--small", help="download thumbnails instead of original images", action="store_true")

    args = parser.parse_args()

    url = "https://boards.4chan.org/" + args.board + "/"
    if args.archive:
        url = url + "archive"

    print("Crawling " + url + " ...")
    threads = list()

    if args.thread:
        threads.append(args.board)
    else:
        if args.archive:
            print("Getting all threads from the archive page ...")
            threads = get_threads_from_archive(url)
        else:
            print("Getting all threads from the board ...")
            threads = get_threads_from_board(url)

    if args.directory:
        out_dir = args.directory

    number_of_threads = len(threads)
    number_of_downloads = 0

    for thread in threads:
        print("Getting all links from thread " + thread)
        images = get_images_in_thread(thread, args.small)

        print("Downloading all images from thread " + thread)
        number_of_downloads = number_of_downloads + download_images(images, out_dir)

    end_time = time.time()

    elapsed_time = end_time - start_time
    converted_time = time.gmtime(elapsed_time)
    formatted_time = time.strftime("%H:%M:%S", converted_time)

    print()
    print("Finished downloading {} image(s) from {} thread(s) in {}!".format(number_of_downloads, number_of_threads, formatted_time))

