from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re
import requests
import os
import json
from tqdm import tqdm
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# SETTINGS
# ==========================================

BACKUP_FOLDER = "Facebook_Backup"

MAX_RETRIES = 3

SCROLL_WAIT = 3

PHOTO_WAIT = 0


# ==========================================
# CREATE BACKUP FOLDER
# ==========================================

if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)


# ==========================================
# START CHROME
# ==========================================

driver = webdriver.Chrome()

driver.get("https://facebook.com")


input(
    "\nLogin to Facebook and press Enter..."
)


input(
    "\nOpen the Albums page and press Enter..."
)


# ==========================================
# AUTOMATIC ALBUM PAGE SCROLLING
# ==========================================

def scroll_page():

    print("\nLoading all albums...")

    previous_album_count = 0
    stable_count = 0

    while stable_count < 5:

        # Scroll slowly
        driver.execute_script(
            "window.scrollBy(0, 800);"
        )

        time.sleep(2)

        links = driver.find_elements(
            By.TAG_NAME,
            "a"
        )

        album_count = 0

        for link in links:

            try:

                href = link.get_attribute(
                    "href"
                )

                if href and "media/set/?set=" in href:

                    album_count += 1

            except StaleElementReferenceException:

                continue

        print(
            "Albums detected:",
            album_count
        )

        if album_count == previous_album_count:

            stable_count += 1

        else:

            stable_count = 0
            previous_album_count = album_count

    print("Finished loading albums")


# ==========================================
# FIND ALL ALBUMS
# ==========================================

def get_albums():

    scroll_page()

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    albums = []

    for link in links:

        href = link.get_attribute(
            "href"
        )

        if href and "media/set/?set=" in href:

            name = link.text.strip()

            if name:

                album_name = name.split("\n")[0]

                albums.append(
                    {
                        "name": album_name,
                        "url": href
                    }
                )

    # Remove duplicates

    unique = []

    seen = set()

    for album in albums:

        if album["url"] not in seen:

            unique.append(album)

            seen.add(
                album["url"]
            )

    return unique


# ==========================================
# GET ALBUM LIST
# ==========================================
albums = get_albums()


print("\n==============================")

print(
    "Albums found:",
    len(albums)
)

print("==============================\n")


for index, album in enumerate(
    albums,
    start=1
):

    print(
        f"{index}. {album['name']}"
    )


# Save album list

with open(
    "albums.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        albums,
        f,
        indent=4,
        ensure_ascii=False
    )


print(
    "\nAlbum list saved."
)

# ==========================================
# GET ALBUM ID
# ==========================================


def get_album_id(url):

    match = re.search(
        r"set=a\.(\d+)",
        url
    )

    if match:

        return match.group(1)

    return None


# ==========================================
# GET PHOTO LINKS FROM ALBUM
# ==========================================

def get_photo_links(album_url):

    driver.get(album_url)

    time.sleep(5)

    album_id = get_album_id(
        driver.current_url
    )

    if not album_id:

        print(
            "Album ID not found"
        )

        return []

    # Scroll album page to load photos

    last_height = 0

    while True:

        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        time.sleep(2)

        new_height = driver.execute_script(
            "return document.body.scrollHeight"
        )

        if new_height == last_height:

            break

        last_height = new_height

    links = driver.find_elements(
        By.TAG_NAME,
        "a"
    )

    photo_links = []

    for link in links:

        href = link.get_attribute(
            "href"
        )

        if (
            href
            and "/photo/?fbid=" in href
            and album_id in href
        ):

            photo_links.append(
                href
            )

    return list(set(photo_links))


# ==========================================
# EXTRACT IMAGE URL WITH RETRY
# ==========================================

def extract_image_url(photo_url):

    for attempt in range(
        MAX_RETRIES
    ):

        try:

            driver.get(
                photo_url
            )

            try:

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME, "img")
                    )
                )

            except:

                pass

            images = driver.find_elements(
                By.TAG_NAME,
                "img"
            )

            largest_image = None

            largest_size = 0

            for img in images:

                src = img.get_attribute(
                    "src"
                )

                if src and (
                    "scontent" in src
                    or "fbcdn" in src
                ):

                    width = img.get_attribute(
                        "width"
                    )

                    height = img.get_attribute(
                        "height"
                    )

                    try:

                        size = (
                            int(width)
                            *
                            int(height)
                        )

                    except:

                        size = 0

                    if size > largest_size:

                        largest_size = size

                        largest_image = src

            if largest_image:

                return largest_image

        except Exception as e:

            print(
                "Retry",
                attempt + 1,
                "failed"
            )

            time.sleep(3)

    return None


# ==========================================
# PROCESS ONE ALBUM
# ==========================================

def get_album_images(album):

    print(
        "\nProcessing:",
        album["name"]
    )

    photos = get_photo_links(
        album["url"]
    )

    print(
        "Photos found:",
        len(photos)
    )

    image_urls = []

    for photo in tqdm(
        photos,
        desc="Extracting",
        unit="photo"
    ):

        image = extract_image_url(
            photo
        )

        if image and image not in image_urls:

            image_urls.append(
                image
            )

    print(
        "Images ready:",
        len(image_urls)
    )

    return image_urls

# ==========================================
# CLEAN FOLDER NAME
# ==========================================


def clean_name(name):

    invalid = [
        "/", "\\", ":", "*",
        "?", "\"", "<", ">",
        "|"
    ]

    for char in invalid:

        name = name.replace(
            char,
            "_"
        )

    return name.strip()


# ==========================================
# CHECK EXISTING FILES
# ==========================================

def get_existing_images(folder):

    if not os.path.exists(folder):

        return set()

    files = set()

    for file in os.listdir(folder):

        if file.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):

            files.add(file)

    return files


# ==========================================
# DOWNLOAD IMAGE WITH RETRY
# ==========================================

def download_image(url, filepath):

    for attempt in range(
        MAX_RETRIES
    ):

        try:

            response = requests.get(
                url,
                timeout=20
            )

            if response.status_code == 200:

                with open(
                    filepath,
                    "wb"
                ) as file:

                    file.write(
                        response.content
                    )

                return True

        except Exception as e:

            print(
                "Download retry",
                attempt + 1
            )

            time.sleep(3)

    return False

# ==========================================
# ESTIMATE TOTAL BACKUP SIZE
# ==========================================


def estimate_backup_size(albums):

    print("\n==============================")
    print("ESTIMATING BACKUP SIZE")
    print("==============================")

    total_photos = 0
    total_bytes = 0

    for album in albums:

        print(
            "\nChecking:",
            album["name"]
        )

        images = get_album_images(
            album
        )

        total_photos += len(images)

        # Size of THIS album only
        album_bytes = 0

        for url in tqdm(
            images,
            desc="Estimating",
            unit="photo"
        ):

            try:

                response = requests.head(
                    url,
                    timeout=20,
                    allow_redirects=True
                )

                size = int(
                    response.headers.get(
                        "Content-Length",
                        0
                    )
                )

                album_bytes += size
                total_bytes += size

            except:

                pass

        # Print album size immediately
        album_mb = album_bytes / (1024 ** 2)

        print(
            f"\nAlbum Size: "
            f"{album_mb:.2f} MB"
        )

        # Running total
        total_gb = total_bytes / (1024 ** 3)

        print(
            f"Running Total: "
            f"{total_gb:.2f} GB"
        )

    total_gb = (
        total_bytes /
        (1024 ** 3)
    )

    print("\n==============================")
    print("ESTIMATION COMPLETE")
    print("==============================")

    print(
        "Albums:",
        len(albums)
    )

    print(
        "Photos:",
        total_photos
    )

    print(
        f"Estimated Size: {total_gb:.2f} GB"
    )

    print("==============================")

    return total_photos, total_gb
# ==========================================
# DOWNLOAD ONE ALBUM
# ==========================================


def download_album(album, album_number, total):

    print("\n================================")
    print(
        f"Album {album_number}/{total}"
    )
    print(
        album["name"]
    )
    print("================================")

    images = get_album_images(
        album
    )

    if not images:

        print(
            "No images found"
        )

        return

    folder_name = clean_name(
        album["name"]
    )

    album_folder = os.path.join(
        BACKUP_FOLDER,
        folder_name
    )

    if not os.path.exists(
        album_folder
    ):

        os.makedirs(
            album_folder
        )

    existing = get_existing_images(
        album_folder
    )

    print(
        "Already downloaded:",
        len(existing)
    )

    print(
        "Starting download..."
    )

    for index, url in enumerate(
        tqdm(
            images,
            desc="Downloading",
            unit="photo"
        ),
        start=1
    ):

        filename = (
            f"photo_{index}.jpg"
        )

        filepath = os.path.join(
            album_folder,
            filename
        )

        # Resume feature

        if filename in existing:

            continue

        success = download_image(
            url,
            filepath
        )

        if success:

            print(
                "Saved:",
                filename
            )

        else:

            print(
                "Failed:",
                filename
            )


# Menu ======================================
print("\n==============================")
print("FACEBOOK BACKUP TOOL")
print("==============================")
print("1. Estimate Backup Size")
print("2. Download Backup")
print("3. Estimate Then Download")
print("==============================")

choice = input(
    "\nChoose an option (1-3): "
)


if choice == "1":

    estimate_backup_size(
        albums
    )

    print(
        "\nEstimation complete."
    )

    driver.quit()
    exit()


elif choice == "2":

    print(
        "\nStarting download..."
    )

    total_albums = len(albums)

    for index, album in enumerate(
        albums,
        start=1
    ):

        download_album(
            album,
            index,
            total_albums
        )


elif choice == "3":

    total_photos, total_gb = (
        estimate_backup_size(
            albums
        )
    )

    answer = input(

        f"\nBackup will download "
        f"{total_photos} photos "
        f"(~{total_gb:.2f} GB).\n"
        f"Continue? (y/n): "

    ).lower()

    if answer != "y":

        print(
            "\nBackup cancelled."
        )

        driver.quit()
        exit()

    print(
        "\nStarting download..."
    )

    total_albums = len(
        albums
    )

    for index, album in enumerate(
        albums,
        start=1
    ):

        download_album(
            album,
            index,
            total_albums
        )

else:

    print(
        "Invalid option."
    )

    driver.quit()
    exit()

# ==========================================
# START DOWNLOAD
# ==========================================

print(
    "\nSTARTING DOWNLOAD..."
)

total_albums = len(
    albums
)

for index, album in enumerate(
    albums,
    start=1
):

    download_album(
        album,
        index,
        total_albums
    )


print("\n================================")

print(
    "FACEBOOK BACKUP COMPLETE"
)

print(
    "Saved in:",
    BACKUP_FOLDER
)

print("================================")


input(
    "\nPress Enter to close..."
)


driver.quit()
