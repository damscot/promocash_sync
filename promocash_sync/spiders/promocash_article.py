# -*- coding: utf-8 -*-
import scrapy
import time
import datetime
import sys
import os
from unidecode import unidecode
from scrapy.http import FormRequest
from scrapy.http import Request
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.utils.response import open_in_browser
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst
from w3lib.html import remove_tags
import re
import mysql.connector
from scrapy import signals

def filter_float(value):
	#print "VALUE1=" + value
	value = re.sub(',','.',value)
	#print "VALUE2=" + value
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
	cbarre = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=TakeFirst(),
	)
	code = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=TakeFirst(),
	)
	name = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii),
		output_processor=Join(''),
	)
	prixht = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=Join(''),
	)
	prixht_promo = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=Join(''),
	)
	prixht_promo_act = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=Join(''),
	)
	prixht_cond = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric, filter_float),
		output_processor=TakeFirst(),
	)
	taxe_css = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, is_css, strip_non_numeric, filter_float),
		output_processor=TakeFirst(),
	)
	tva = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric ,strip_tva),
		output_processor=TakeFirst(),
	)
	marque = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii),
		output_processor=TakeFirst(),
	)
	cond = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric, filter_float),
		output_processor=TakeFirst(),
	)
	unite_achat = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, check_unite_achat, strip_non_numeric, filter_float),
		output_processor=TakeFirst(),
	)
	image = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string),
		output_processor=TakeFirst(),
	)
	last_updated = scrapy.Field(serializer=str)
	
	def show(self):
		print "***********************"
		print dict(self)
		print "***********************"
	
	def insert(self, spider):
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
			if (not ('prixht_promo' in elem)):
				elem['prixht'] = re.sub(',','.',elem['prixht_promo_act'])
				elem['prixht_promo'] = elem['prixht_promo_act']
			else:
				elem['prixht'] = re.sub(',','.',elem['prixht_promo'])
		else:
			elem['prixht'] = re.sub(',','.',elem['prixht'])
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
		spider.cursor.execute("""INSERT INTO Articles (cbarre, code, name, prixht, prixht_promo, prixht_promo_act, prixht_unite, prixht_cond, taxe_css, tva, marque, unite_achat, cond, image, last_update) 
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
		spider.conn.commit()

class PromocashSyncArticleSpider(CrawlSpider):
	name = 'promocash_article'
	allowed_domains = ['grenoble.promocash.com']
	start_urls = ['https://grenoble.promocash.com/authentification.php']

	def __init__(self, *args, **kwargs):
		super(PromocashSyncArticleSpider, self).__init__(*args, **kwargs)
		
		with open(os.environ['HOME'] + '/promocash/promologin.txt') as f:
			credentials = [x.strip().split(':') for x in f.readlines()]
  
		for username,password in credentials:
			self.promo_user = username
			self.promo_pass = password
		
		with open(os.environ['HOME'] + '/promocash/dblogin.txt') as f:
		  credentials = [x.strip().split(':') for x in f.readlines()]
		  
		for host,username,password in credentials:
			db_host = host
			db_user = username
			db_pass = password
		
		try:
			self.conn = mysql.connector.connect(host=db_host,user=db_user,password=db_pass, database="Promocash")
			self.conn_Laurux = mysql.connector.connect(host=db_host,user=db_user,password=db_pass, database="Laurux01")
			self.cursor = self.conn.cursor()
			self.cursor_Laurux = self.conn_Laurux.cursor(named_tuple=True)
			
		except mysql.connector.Error as err:
			if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
				print "Something is wrong with your user name or password"
			elif err.errno == errorcode.ER_BAD_DB_ERROR:
				print "Database does not exist"
			else:
				print err
				
				
		self.cursor.execute("""
		CREATE TABLE IF NOT EXISTS Articles (
			cbarre varchar(20) NOT NULL,
			code varchar(10) NOT NULL,
			name varchar(200) DEFAULT NULL,
			prixht varchar(8) DEFAULT NULL,
			prixht_promo varchar(8) DEFAULT NULL,
			prixht_promo_act varchar(8) DEFAULT NULL,
			prixht_unite varchar(8) DEFAULT NULL,
			prixht_cond varchar(8) DEFAULT NULL,
			taxe_css varchar(8) DEFAULT NULL,
			tva varchar(5) DEFAULT NULL,
			marque varchar(20) DEFAULT NULL,
			unite_achat varchar(8) DEFAULT NULL,
			cond varchar(8) DEFAULT NULL,
			image varchar(200) DEFAULT NULL,
			last_update varchar(20) DEFAULT NULL,
			PRIMARY KEY(cbarre)
		);
		""")
		
		self.cursor_Laurux.execute("""SELECT * FROM Laurux01.Fiches_Art where
					art_four = 401002 and art_code = art_cbarre and art_stocke = 1 and art_suspendu = 0;
					""")
		
		self.cbarre_notfound = []
		
		#change to True for testing
		if (False):
			self.cbarre_list = ["3336770000566"]
		else:
			self.cbarre_list = []
			for row in self.cursor_Laurux:
				self.cbarre_list.append(row.art_code)
		
		print "*********************"
		print self.cbarre_list
		print "*********************"
		print len(self.cbarre_list)
		print "*********************"
	
	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = super(PromocashSyncArticleSpider, cls).from_crawler(crawler, *args, **kwargs)
		crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		return spider
	
	def parse_start_url(self, response):
		self.logger.warning("Starting Connection with User : " + self.promo_user)
		#open_in_browser(response)
		request = scrapy.FormRequest.from_response(response,formnumber=1,
			formdata={'CLI_NUMERO': self.promo_user,'CLI_PASSWORD': self.promo_pass},
			clickdata={'name':'logClient'},
			callback=self.after_login)
		request.meta['dont_redirect'] = True
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
			return Request(url="https://grenoble.promocash.com",
				callback=self.start_page)
	
	def start_page(self, response):
		time.sleep(1)
		#open_in_browser(response)
		self.logger.warning("Start Page")
		for cbarre in self.cbarre_list:
			request = scrapy.FormRequest.from_response(response,formnumber=1,
				formdata={'searchString': cbarre},
				callback=self.parse_item)
			request.meta['cbarre'] = cbarre
			yield request
	
	def parse_item(self, response):
		self.logger.warning("Parse Item " + response.meta['cbarre'])
		time.sleep(0.5)
		#open_in_browser(response)
		try:
			url_detail = response.xpath('//div[@class="listeProduit"]//div[@class="pdt-libelle"]/a/@href').extract()
			url_detail = u'https://grenoble.promocash.com' + url_detail[0]
		except:
			self.cbarre_notfound.append(response.meta['cbarre'])
			return None
		#print "url_detail: " + url_detail
		request = scrapy.Request(url_detail, callback=self.parse_detail)
		request.meta['cbarre'] = response.meta['cbarre']
		request.meta['name'] = response.xpath('//div[@class="listeProduit"]//div[@class="pdt-libelle"]/a/text()').extract()
		return request
		
	def parse_detail(self, response):
		time.sleep(0.5)
		#open_in_browser(response)
		l = ItemLoader(item=Article(), response=response)
		l.add_value('cbarre', response.meta['cbarre'])
		l.add_xpath('code','//div[@id="produit"]//div[@class="pdt-ifls"]/text()')
		l.add_value('name', response.meta['name'])
		l.add_xpath('cond','//div[@id="produit"]//div[@class="pdt-cond"]/text()')
		l.add_xpath('unite_achat','//div[@id="produit"]//div[@class="pdt-cond"]/text()')
		l.add_xpath('marque','//div[@id="produit"]//div[@class="pdt-marque"]/text()')
		l.add_xpath('prixht','//div[@id="colonneDroiteProduit"]//div[@class="prix"]/span/span[@*]/text()')
		l.add_xpath('prixht_promo','//div[@id="colonneDroiteProduit"]//div[contains(concat(" ", @class, " "), "blocPrix")]/del/text()')
		l.add_xpath('prixht_promo_act','//div[@id="colonneDroiteProduit"]//div[contains(concat(" ", @class, " "), "blocPrix")]/ins/span/span[@*]/text()')
		l.add_xpath('prixht_cond','//div[@id="colonneDroiteProduit"]//div[@class="pdt-pxUnit"]/text()')
		l.add_xpath('taxe_css','//div[@id="colonneDroiteProduit"]//div[@class="pdt-secu"]/text()')
		l.add_xpath('tva','//div[@id="colonneDroiteProduit"]//div[@class="tva"]/span/text()')
		l.add_xpath('image','//div[@id="produit"]//div[@class="imgContainer"]/img[@id="produitIMG"]/@src')
		l.load_item()
		l.item.insert(spider=self)
		l.item.show()
		
	def spider_opened(self, spider):
		self.logger.info('Promocash spider opened: %s', spider.name)
		
	def spider_closed(self, spider):
		self.logger.info('Promocash spider closed: %s', spider.name)
		print "////// NOT FOUND //////"
		print self.cbarre_notfound
		print "///////////////////////"
		try:
			self.cursor.close()
			self.conn.close()
			self.cursor_Laurux.close()
			self.conn_Laurux.close()
		except:
			print "failure during close connection"



