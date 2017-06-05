#!/bin/bash
source $HOME/promocash/bin/activate

com=$(zenity --entry --title="Numero de Commande Promocash" --text="Numero (4 dernier chiffre uniquement)")
com=`echo $com | sed -e 's/ //g'`

if [[ $((com + 0)) -gt 0 && $((com + 0)) -lt 10000 ]] ; then
	# run scrapy
	scrapy runspider $HOME/promocash_sync/promocash_sync/spiders/promocash_commande_complete.py --nolog -a commande=$com > $HOME/Bureau/commande_$com.txt
	zenity --text-info --height 600 --width 800 --filename=$HOME/Bureau/commande_$com.txt
else
	zenity --error --text="commande $com invalide"
fi

