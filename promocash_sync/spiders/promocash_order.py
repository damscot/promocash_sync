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

with open(os.environ['HOME'] + '/promocash/promologin.txt') as f:
  credentials = [x.strip().split(':') for x in f.readlines()]
  
for username,password in credentials:
	promo_user = username
	promo_pass = password

with open(os.environ['HOME'] + '/promocash/dblogin.txt') as f:
  credentials = [x.strip().split(':') for x in f.readlines()]
  
for username,password in credentials:
	db_user = username
	db_pass = password

try:
	conn = mysql.connector.connect(host="localhost",user=db_user,password=db_pass, database="Promocash")
	conn_Laurux = mysql.connector.connect(host="localhost",user=db_user,password=db_pass, database="Laurux01")
	cursor = conn.cursor()
	cursor_Laurux = conn_Laurux.cursor(named_tuple=True)
	
except mysql.connector.Error as err:
	if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
		print "Something is wrong with your user name or password"
	elif err.errno == errorcode.ER_BAD_DB_ERROR:
		print "Database does not exist"
	else:
		print err

cursor.execute("""
CREATE TABLE IF NOT EXISTS Articles (
	cbarre varchar(20) NOT NULL,
	code varchar(10) NOT NULL,
	name varchar(100) DEFAULT NULL,
	prixht varchar(8) DEFAULT NULL,
	prixht_promo varchar(8) DEFAULT NULL,
	prixht_promo_act varchar(8) DEFAULT NULL,
	prixht_unite varchar(8) DEFAULT NULL,
	prixht_cond varchar(8) DEFAULT NULL,
	taxe_css varchar(8) DEFAULT NULL,
	tva varchar(5) DEFAULT NULL,
	marque varchar(20) DEFAULT NULL,
	unite_achat varchar(5) DEFAULT NULL,
	cond varchar(5) DEFAULT NULL,
	image varchar(200) DEFAULT NULL,
	last_update varchar(20) DEFAULT NULL,
	PRIMARY KEY(cbarre)
);
""")

cursor_Laurux.execute("""SELECT * FROM Laurux01.Fiches_Art where
			art_four = 401002 and art_code = art_cbarre and art_stocke = 1 and art_suspendu = 0;
			""")

cbarre_notfound = []

#change to True for testing
if (True):
	#order_list = ["3560070756100","5410228230441"]
	order_list = [{'cbarre' : "3560070756100", 'qte' : "2" }, {'cbarre' : "5410228230441", 'qte' : "11"}]
else:
	order_list = []
	for row in cursor_Laurux:
		order_list.append(row.art_code)

print "*********************"
print order_list
print "*********************"
print len(order_list)
print "*********************"
#sys.exit(0)

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

class Article(scrapy.Item):
	
	def show(self):
		print "***********************"
		print dict(self)
		print "***********************"
	
	def insert(self):
		elem=dict(self)
		if (not ('taxe_css' in elem)):
			 elem['taxe_css'] = "0"
		if (not ('cond' in elem)):
			 elem['cond'] = "1"
		if (not ('unite_achat' in elem)):
			 elem['unite_achat'] = "1"
		if (not ('marque' in elem)):
			 elem['marque'] = ""
		if (not ('prixht' in elem)):
			 elem['prixht'] = elem['prixht_promo']
		else:
			if (not ('prixht_promo' in elem)):
				elem['prixht_promo'] = elem['prixht']
			if (not ('prixht_promo_act' in elem)):
				elem['prixht_promo_act'] = elem['prixht']
		if (not ('image' in elem)):
			elem['image'] = ""
		if (('prixht_cond' in elem) and (float(elem['cond']) != "{:.3f}".format(float(elem['prixht']) / float(elem['prixht_cond'])))):
			elem['cond'] = "{:.3f}".format(float(elem['prixht']) / float(elem['prixht_cond']))
		if (not ('prixht_unite' in elem)):
			elem['prixht_unite'] = "{:.2f}".format(float(elem['prixht']) / float(elem['unite_achat']))
		today = datetime.datetime.today()
		elem['last_update'] = today.strftime("%Y-%m-%d %H:%M:%S")
		cursor.execute("""INSERT INTO Articles (cbarre, code, name, prixht, prixht_promo, prixht_promo_act, prixht_unite, prixht_cond, taxe_css, tva, marque, unite_achat, cond, image, last_update) 
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
			code = VALUES(code),
			name = VALUES(name),
			prixht = VALUES(prixht),
			prixht_promo = VALUES(prixht_promo),
			prixht_promo_act = VALUES(prixht_promo_act),
			prixht_unite = VALUES(prixht_unite),
			prixht_cond = VALUES(prixht_cond),
			taxe_css = VALUES(taxe_css),
			tva = VALUES(tva),
			marque = VALUES(marque),
			unite_achat = VALUES(unite_achat),
			cond = VALUES(cond),
			marque = VALUES(marque),
			image = VALUES(image),
			last_update = VALUES(last_update) ;
			""",(elem['cbarre'], elem['code'], elem['name'], elem['prixht'],
			elem['prixht_promo'], elem['prixht_promo_act'], elem['prixht_unite'], elem['prixht_cond'],
			elem['taxe_css'], elem['tva'], elem['marque'], elem['unite_achat'], elem['cond'],
			elem['image'], elem['last_update']))
		conn.commit()

class PromocashOrderArticleSpider(CrawlSpider):
	name = 'promocash_order'
	allowed_domains = ['grenoble.promocash.com']
	start_urls = ['https://grenoble.promocash.com/authentification.php']

	#rules = (
	#	Rule(LinkExtractor(allow=('https://grenoble.promocash.com/robots\.txt')), callback='start_session', follow=False),
	#	Rule(LinkExtractor(allow=('https://grenoble.promocash.com/authentification\.php', ), deny=('cmdEtape1\.php', )), callback='parse_start_url', follow=False),
	#	Rule(LinkExtractor(allow=('produitListe\.php')), callback='parse_item', follow=True),
	#)
	
	def __init__(self):
		# Path for geckodriver
		os.environ["PATH"] += ":" + os.environ['HOME'] + "/promocash_sync/"
	
	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = super(PromocashOrderArticleSpider, cls).from_crawler(crawler, *args, **kwargs)
		crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		return spider
	
	def start_session(self, response):
		self.logger.warning("Start Session")
		return
	
	def parse_start_url(self, response):
		self.logger.warning("Starting Connection with User : " + promo_user)
		request = scrapy.FormRequest.from_response(response,formnumber=1,
			formdata={'CLI_NUMERO': promo_user,'CLI_PASSWORD': promo_pass},
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
		username.send_keys(promo_user)
		password.send_keys(promo_pass)
		login_btn = self.driver.find_element_by_name("logClient")
		login_btn.click()
		yield request
	
	#def after_user(self, response):
	#	time.sleep(1)
	#	open_in_browser(response)
	#	self.logger.warning("Enter Password " + promo_user)
	#	req = FormRequest.from_response(response,formnumber=1,
	#		formdata={'CLI_NUMERO': promo_user,'CLI_PASSWORD': promo_pass},
	#		clickdata={'name':'logClient'},
	#		callback=self.after_login)
	#	puts req
	#	yield req
	
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
		
		for order in order_list:
			request = scrapy.FormRequest.from_response(response,formnumber=1,
				formdata={'searchString': order['cbarre']},
				callback=self.order_item)
			request.meta['cbarre'] = order['cbarre']
			request.meta['qte'] = order['qte']
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
			cbarre_notfound.append(response.meta['cbarre'])
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
		print cbarre_notfound
		print "///////////////////////"
		try:
			self.driver.close()
			if HEADLESS:
				self.display.stop()
			cursor.close()
			conn.close()
			cursor_Laurux.close()
			conn_Laurux.close()
		except:
			print "failure during close connection"



