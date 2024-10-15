from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By

# Set up the WebDriver (for Chrome, replace with the path to your downloaded ChromeDriver)
service = Service('/home/usboot/Downloads/geckodriver')  # Update this path
driver = webdriver.Firefox(service=service, )

# Navigate to the page
url = "https://www.tandfonline.com/doi/full/10.1080/07303084.2016.1270786"
driver.get(url)

# Get the page content
page_content = driver.page_source

# Print or save the content
print(page_content)

# Close the browser
driver.quit()
