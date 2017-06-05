#!/bin/bash
source $HOME/promocash/bin/activate
scrapy runspider $HOME/promocash_sync/promocash_sync/spiders/promocash_article.py

