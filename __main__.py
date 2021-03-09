import time
from urllib.parse import urldefrag
import os
import errno
import requests
import argparse
from bs4 import BeautifulSoup

exclude_url_parts = ["contest_banner", "archived", "closed", "sticky", "modicon", "adminicon"]
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
        # Remove the last part of the url that gets added when referring to the thread from the archive.
        # We want a clean url so we can use it to create clean subdirectory names.
        thread = thread.rpartition("/")[0]
        threads.append(thread)

    print("Found the following " + str(len(threads)) + " threads:")
    for thread in threads:
        print(thread)

    return threads


def make_directory(dir_name):
    if not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


# If the subdirectories argument is set, pass the base directory of the crawler to the base_dir parameter.
# Otherwise, leave it empty.
def get_images_in_thread(url, small, exclude_strings, base_dir=""):
    html_page = requests.get(url).text
    soup = BeautifulSoup(html_page, "lxml")

    images = list()

    # Filter thread
    subject = soup.find("span", class_="subject").string
    first_post = soup.find("blockquote", class_="postMessage").string

    if exclude_strings:
        if any(string in subject for string in exclude_strings):
            return images
        if any(string in first_post for string in exclude_strings):
            return images

    subdirectory = base_dir

    if base_dir:
        subdirectory = os.path.join(base_dir, url.split("/")[-1])
        make_directory(subdirectory)

    if small:
        for image in soup.find_all("img"):
            src = "https:" + image.get("src")
            if any(string in src for string in exclude_url_parts):
                continue
            if any(format in src for format in media_formats):
                print("Found image " + src)
                images.append(src)
    else:
        for image in soup.find_all("a", class_="fileThumb"):
            src = "https:" + image.get("href")
            if any(string in src for string in exclude_url_parts):
                continue
            if any(format in src for format in media_formats):
                print("Found image " + src)
                images.append(src)

    return images, subdirectory


def download_images(images, dir_name):
    make_directory(dir_name)

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

    dir = os.getcwd()

    parser = argparse.ArgumentParser(description="4chan image crawler - download all images from a board or a thread")

    parser.add_argument("board", help="board to download the images from")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-a", "--archive", help="download images from all threads in the archive", action="store_true")
    group.add_argument("-t", "--thread", help="replace the board with a link to a specific thread", action="store_true")

    parser.add_argument("-d", "--directory", help="save files to special directory", default=dir)
    parser.add_argument("-s", "--small", help="download thumbnails instead of original images", action="store_true")
    parser.add_argument("-e", "--exclude", help="comma-separated list of terms to search for in the thread subject and first post. If found, the thread will be excluded from downloading")
    parser.add_argument("-S", "--subdirectories", help="create a subdirectory for each thread", action="store_true")

    args = parser.parse_args()

    exclude_strings = args.exclude

    if exclude_strings:
        if exclude_strings.find(",") != -1:
            exclude_strings = args.exclude.split(',')

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
        dir = args.directory

    number_of_threads = len(threads)
    number_of_downloads = 0

    for thread in threads:
        out_dir = dir
        print("Getting all links from thread " + thread)
        if args.subdirectories:
            images, out_dir = get_images_in_thread(thread, args.small, exclude_strings, out_dir)
        else:
            images, empty_dir = get_images_in_thread(thread, args.small, exclude_strings)

        if not images:
            print("Found excluding string in thread, skipping ...")
            continue

        print("Downloading all images from thread " + thread)
        number_of_downloads = number_of_downloads + download_images(images, out_dir)

    end_time = time.time()

    elapsed_time = end_time - start_time
    converted_time = time.gmtime(elapsed_time)
    formatted_time = time.strftime("%H:%M:%S", converted_time)

    print()
    print("Finished downloading {} image(s) from {} thread(s) in {}!".format(number_of_downloads, number_of_threads, formatted_time))

