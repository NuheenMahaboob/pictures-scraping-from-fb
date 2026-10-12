from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re


driver = webdriver.Chrome()


# Open Facebook
driver.get("https://facebook.com")


input("Login and press Enter...")


input("Open an album page and press Enter...")


# -----------------------------
# Get album ID
# -----------------------------

album_url = driver.current_url

print("\nAlbum URL:")
print(album_url)


match = re.search(r"set=a\.(\d+)", album_url)


if match:

    album_id = match.group(1)

    print("Album ID:", album_id)

else:

    print("Could not find album ID")

    driver.quit()
    exit()



# -----------------------------
# Find photo links
# -----------------------------

links = driver.find_elements(By.TAG_NAME, "a")


photo_links = []


for link in links:

    href = link.get_attribute("href")


    if href and "/photo/?fbid=" in href and album_id in href:

        photo_links.append(href)



# Remove duplicates

photo_links = list(set(photo_links))


print("\nFound", len(photo_links), "photo links")


for p in photo_links:

    print(p)




# -----------------------------
# Extract images
# -----------------------------

image_urls = []


for index, photo in enumerate(photo_links):


    print(f"\nOpening photo {index+1}/{len(photo_links)}")


    driver.get(photo)


    time.sleep(4)



    images = driver.find_elements(By.TAG_NAME, "img")


    largest_image = None

    largest_size = 0



    for img in images:


        src = img.get_attribute("src")


        if src and ("scontent" in src or "fbcdn" in src):


            width = img.get_attribute("width")

            height = img.get_attribute("height")



            try:

                size = int(width) * int(height)

            except:

                size = 0



            if size > largest_size:

                largest_size = size

                largest_image = src




    if largest_image:


        # Replace thumbnail size with larger size

        largest_image = largest_image.replace(
            "s100x100",
            "s2048x2048"
        )


        if largest_image not in image_urls:

            image_urls.append(largest_image)



        print("Found image:")
        print(largest_image[:150])


    else:

        print("No image found")





# -----------------------------
# Final result
# -----------------------------

print("\n====================")

print("Total images found:", len(image_urls))

print("====================\n")


for i, img in enumerate(image_urls, start=1):

    print(f"{i}. {img}")



input("\nPress Enter to close...")

driver.quit()