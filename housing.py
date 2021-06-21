from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class Housing:
	def __init__(self):
		chrome_options = Options()
		chrome_options = Options()
		chrome_options.add_argument('--headless')
		chrome_options.add_argument("--disable-gpu")
		chrome_options.add_argument('--no-sandbox')
		chrome_options.add_argument('log-level=2')
		chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
		driver = webdriver.Chrome(options=chrome_options)
		self.url = "https://prometheusapartments.com/ca/san-mateo-apartments/chesapeake-point/lease/?OLL-source-attribution=Website/PrometheusApartments.com#k=51370"
		self.driver = driver

	def scrape(self):
		#navigate to website
		self.driver.get(self.url)	
		iframe = self.driver.find_element_by_xpath("/html/body/main/section[3]/div/div/div/div/iframe")
		self.driver.switch_to.frame(iframe)
		#preliminary buttons
		welcome_btn = "/html/body/ui-view/rp-widget/div[2]/div/div/div/div/div[2]/div/button"
		WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.XPATH, welcome_btn))).click()
		menu_btn = "/html/body/ui-view/rp-widget/div[4]/div[1]/div/div[1]/div/div/div[3]/a"
		WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, menu_btn))).click()
		#scrape availabilities
		availability_dict = {}
		for i in range(1,6):
			house_type = self.driver.find_element_by_xpath(f"/html/body/ui-view/rp-widget/div[4]/div[2]/main/div[2]/div[{i}]/div[3]/span[1]").text
			availability = self.driver.find_element_by_xpath(f"/html/body/ui-view/rp-widget/div[4]/div[2]/main/div[2]/div[{i}]/div[4]/button").text
			if availability == "Check Availability":
				availability = "(0) Available"
			availability_dict[house_type] = availability

		return availability_dict

#Sanitize Input
def sanitize_input_string(prompt, *options):
    answer = ""
    while True:
        try:
            answer = str(input(prompt))
            if answer.isdigit():
            	print("Please give a string")
            	continue
        except ValueError:
            print("Please give a string")
            continue
        if options != () and answer not in options[0]:
            print(f"Please choose from the given options: {options[0]}")
            continue
        else:
            break
    return answer.lower()


def execute():
	chesapeake = Housing()
	availability_dict = chesapeake.scrape()
	return availability_dict