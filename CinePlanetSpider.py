import json
from datetime import datetime
from time import sleep
import scrapy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class CinePlanetSpider(scrapy.Spider):
    name = 'CinePlanetSpider'
    timestemp = datetime.now().strftime("%d_%b_%Y_%H_%M_%S")
    custom_settings = {'ROBOTSTXT_OBEY': False,
                       'FEED_URI': f'outputs/CinePlanet_{timestemp}.csv',
                       'FEED_FORMAT': 'csv',
                       'FEED_EXPORT_ENCODING': 'utf-8',
                       }

    def __init__(self, *args, **kwargs):
        super(CinePlanetSpider, self).__init__(*args, **kwargs)
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)

    main_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    }
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache, no-store',
        'content-type': 'application/json',
        'ocp-apim-subscription-key': 'c6f97c336b60469189a010a5836fe891',
        'priority': 'u=1, i',
        'referer': 'https://www.cineplanet.cl/peliculas',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    }

    def start_requests(self):
        yield scrapy.Request('https://www.cineplanet.cl/', headers=self.main_headers)

    def _parse(self, response, **kwargs):
        url = 'https://www.cineplanet.cl/api/cache/moviescache'
        yield scrapy.Request(url, headers=self.headers, callback=self.parse)

    def parse(self, response, **kwargs):
        films = json.loads(response.body).get('movies', [])
        for film in films[:]:
            date_str = film.get('OpeningDate', '')
            date = datetime.fromisoformat(date_str).date()
            current_date = datetime.now().date()
            if not film.get('isComingSoon') and date <= current_date:
                # print(json.dumps(film))
                for cinema in film.get('cinemas', [])[:]:
                    for date in cinema.get('dates', [])[:]:
                        for session in date.get('sessions', [])[:]:
                            self.driver = webdriver.Chrome(options=self.options)
                            try:
                                cinema = session.split('-')[0]
                                session_id = session.split('-')[1]
                                seats_url = 'https://www.cineplanet.cl/compra/{}/{}/{}/asientos'.format(
                                    film.get('movieDetailsUrl', ''), cinema, session_id)
                                self.driver.get(seats_url)
                                WebDriverWait(self.driver, 25).until(EC.presence_of_element_located(
                                    (By.XPATH, '//div[div/div/div[@class="seat-map--seat seat-map--seat_available"]]')))
                                self.driver.find_element(by=By.XPATH,
                                                         value='//div[div/div/div[@class="seat-map--seat seat-map--seat_available"]]').click()
                                sleep(2)
                                self.driver.find_element(by=By.XPATH,
                                                         value='//button[span[contains(text(), "Continuar")]]').click()
                                WebDriverWait(self.driver, 25).until(EC.presence_of_element_located(
                                    (By.XPATH, '//button[span/span[contains(text(), "Seguir como invitado")]]')))
                                self.driver.find_element(by=By.XPATH,
                                                         value='//button[span/span[contains(text(), "Seguir como invitado")]]').click()
                                WebDriverWait(self.driver, 25).until(EC.presence_of_element_located((By.XPATH,
                                                                                                     '//div[@class="purchase-tickets--common-tickets-categories--description-wrapper"]')))
                                response = scrapy.Selector(text=self.driver.page_source)
                                cats = response.xpath(
                                    '//div[@class="purchase-tickets--common-tickets-categories--description-wrapper"]')
                                for cat in cats:
                                    item = dict()
                                    item['CinePlanet Name'] = response.xpath(
                                        '//div[@class="cart-desktop--session-cinema"]/text()').get('')
                                    item['Movie Name'] = response.xpath(
                                        '//div[@class="cart-desktop--movie-title"]/text()').get('')
                                    item['Date'] = ' '.join(response.xpath(
                                        '//div[@class="cart-desktop--session-date"]/text()').getall()).strip()
                                    item['Movie Attributes'] = ' '.join(response.xpath(
                                        '//div[@class="cart-desktop--movie-attributes"]/text()').getall()).strip()
                                    item['Show Time'] = ' '.join(response.xpath(
                                        '//div[@class="cart-desktop--session--time"]/text()').getall()).strip()
                                    item['Category Title'] = cat.xpath(
                                        './div[@class="purchase-tickets--common-tickets-categories--title"]/text()').get(
                                        '').strip()
                                    item['Category Price'] = cat.xpath(
                                        './div[@class="purchase-tickets--common-tickets-categories--price"]/span/text()').get(
                                        '').strip()
                                    yield item
                            except:
                                pass
                            self.driver.close()
