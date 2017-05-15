# -*- coding: utf-8 -*-
import scrapy
import time
import datetime
import sys
import os
import os.path
import re
import mysql.connector
import codecs

from pyvirtualdisplay import Display
from unidecode import unidecode

from scrapy import signals
from scrapy.http import FormRequest
from scrapy.http import Request
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.utils.response import open_in_browser
from scrapy.utils.project import get_project_settings
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst

from w3lib.html import remove_tags

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

HEADLESS = False
settings = get_project_settings()

def filter_float(value):
	value = re.sub(',','.',value)
	try:
		f = float(value)
		return f
	except ValueError:
		return False
		
def strip_tva(value):
	return re.sub('%','',value)
	
def strip_string(value):
	#print "VALUE1=" + value
	#print "VALUE2=" + re.sub('\s+',' ',value).strip()
	return re.sub('\s+',' ',value).strip()

def strip_non_numeric(value):
	non_decimal = re.compile(r'[^\d.,]+')
	return non_decimal.sub('', value)

def is_css(value):
	if "securite sociale" in value:
		return value
	else:
		return None

def unicode_to_ascii(value):
	return unidecode(value)

def check_unite_achat(value):
	if "Vendu par" in value:
		return value
	else:
		return "1"

def show_field(value):
	print "Field: " + value
	return value

class PromocashOrderArticleSpider(CrawlSpider):
	name = 'promocash_order'
	allowed_domains = ['grenoble.promocash.com']
	start_urls = ['https://grenoble.promocash.com/authentification.php']
	
	def __init__(self, commande=None, *args, **kwargs):
		super(PromocashOrderArticleSpider, self).__init__(*args, **kwargs)
		# Path for geckodriver
		os.environ["PATH"] += ":" + os.environ['HOME'] + "/promocash_sync/"
		
		if commande == None :
			print "ERREUR! le numero de la commande doit etre fourni '-a commande=XXXXX"
			sys.exit(-1)
		print "COMMANDE = " + commande
		self.commande = commande
		
		with open(os.environ['HOME'] + '/promocash/promologin.txt') as f:
			credentials = [x.strip().split(':') for x in f.readlines()]
  
		for username,password in credentials:
			self.promo_user = username
			self.promo_pass = password
		
		with open(os.environ['HOME'] + '/promocash/dblogin.txt') as f:
		  credentials = [x.strip().split(':') for x in f.readlines()]
		  
		for username,password in credentials:
			db_user = username
			db_pass = password
		
		try:
			self.conn = mysql.connector.connect(host="localhost",user=db_user,password=db_pass, database="Promocash")
			self.conn_Laurux = mysql.connector.connect(host="localhost",user=db_user,password=db_pass, database="Laurux01")
			self.cursor = self.conn.cursor()
			self.cursor_Laurux = self.conn_Laurux.cursor(named_tuple=True)
			
		except mysql.connector.Error as err:
			if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
				print "Something is wrong with your user name or password"
			elif err.errno == errorcode.ER_BAD_DB_ERROR:
				print "Database does not exist"
			else:
				print err
		
		self.cursor_Laurux.execute("""SELECT * FROM Laurux01.Fiches_Ligcom where
					four = 401002 and numcom = %s""", (commande,))
		
		self.cbarre_notfound = []
		
		#change to True for testing
		if (True):
			#self.order_list = ["3560070756100","5410228230441"]
			self.order_list = [{'cbarre' : "3560070756100", 'qte' : "2" }, {'cbarre' : "5410228230441", 'qte' : "5"}]
		else:
			self.order_list = []
			for row in self.cursor_Laurux:
				self.order_list.append({'cbarre' : row.code , 'qte' : row.qte})
			self.order_list = self.order_list[:4]
		
		print "*********************"
		print self.order_list
		print "*********************"
		print len(self.order_list)
		print "*********************"
		
	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		print "TOTO"
		spider = super(PromocashOrderArticleSpider, cls).from_crawler(crawler, *args, **kwargs)
		crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		return spider
	
	def start_session(self, response):
		self.logger.warning("Start Session")
		return
	
	def parse_start_url(self, response):
		self.logger.warning("Starting Connection with User : " + self.promo_user)
		request = scrapy.FormRequest.from_response(response,formnumber=1,
			formdata={'CLI_NUMERO': self.promo_user,'CLI_PASSWORD': self.promo_pass},
			clickdata={'name':'logClient'},
			callback=self.after_login)
		request.meta['dont_redirect'] = True
		#login in selenium session too
		self.driver.get(response.url)
		WebDriverWait(self.driver, 10)
		banner = self.driver.find_element_by_id("cookie-banner-close")
		banner.click()
		username = self.driver.find_element_by_name("CLI_NUMERO")
		password = self.driver.find_element_by_name("CLI_PASSWORD")
		username.send_keys(self.promo_user)
		password.send_keys(self.promo_pass)
		login_btn = self.driver.find_element_by_name("logClient")
		login_btn.click()
		yield request
	
	def after_login(self, response):
		self.logger.warning("Check logging")
		time.sleep(0.2)
		#open_in_browser(response)
		if "Merci de vérifier notre numéro de carte" in response.body:
			self.logger.warning("logging Failed")
			return
		else:
			self.logger.warning("logging Successfull")
			return Request(url="https://grenoble.promocash.com/",
				callback=self.start_page)
	
	def start_page(self, response):
		time.sleep(1)
		self.logger.warning("Start Page")
		
		for order in self.order_list:
			request = scrapy.FormRequest.from_response(response,formnumber=1,
				formdata={'searchString': order['cbarre']},
				callback=self.order_item)
			request.meta['cbarre'] = order['cbarre']
			
			self.cursor.execute("""SELECT * FROM Articles where
					cbarre = %s""", (order['cbarre'],))
			request.meta['qte'] = ceil(order['qte'] / (self.cursor[0].unite_achat))
			yield request
	
	def order_item(self, response):
		self.logger.warning("Order Item " + response.meta['cbarre'] + " => Qte " + response.meta['qte'])
		response.meta['driver'] = self.driver
		time.sleep(0.5)
		#open_in_browser(response)
		try:
			url_detail = response.xpath('//div[@class="listeProduit"]//div[@class="pdt-libelle"]/a/@href').extract()
			url_detail = u'https://grenoble.promocash.com' + url_detail[0]
		except:
			self.cbarre_notfound.append(response.meta['cbarre'])
			return None
		
		self.driver.get(url_detail)
		#f = codecs.open("out_" + response.meta['cbarre'] + ".html", 'w', "utf-8")
		#f.write(self.driver.page_source)
		#f.flush()
		#f.close()
		qte = WebDriverWait(self.driver, 10).until(
			EC.visibility_of_element_located((By.ID, 'PRO_QUANTITE'))
		)
		qte.clear()
		qte.send_keys(response.meta['qte'])
		order_btn = WebDriverWait(self.driver, 10).until(
			EC.visibility_of_element_located((By.XPATH, '//input[@id="SUBM"]'))
		)
		order_btn.click()
		return None
		
	def spider_opened(self, spider):
		self.logger.info('Promocash spider opened: %s', spider.name)
		if HEADLESS:
			self.display = Display(visible=0, size=(1280, 1024))
			self.display.start()
		firefox_path = settings.get('FIREFOX_EXE')
		if (firefox_path == ""):
			firefox_path = '/usr/lib/firefox/firefox'
		binary = FirefoxBinary(firefox_path)
		firefox_capabilities = DesiredCapabilities.FIREFOX
		firefox_capabilities['binary'] = firefox_path
		self.driver = webdriver.firefox.webdriver.WebDriver(capabilities=firefox_capabilities, firefox_binary=binary)
	
	def spider_closed(self, spider):
		self.logger.info('Promocash spider closed: %s', spider.name)
		print "////// NOT FOUND //////"
		print self.cbarre_notfound
		print "///////////////////////"
		try:
			self.driver.close()
			if HEADLESS:
				self.display.stop()
			self.cursor.close()
			self.conn.close()
			self.cursor_Laurux.close()
			self.conn_Laurux.close()
		except:
			print "failure during close connection"



