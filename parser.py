from bs4 import BeautifulSoup
from requests import get
import logging
import ujson
import os
import collections 
from decomposer import _decompose

url = "https://escapefromtarkov.gamepedia.com/Weapon_mods"

# Declaring lists
headlines = []
tmp_tabs = []
cleaned_tabs = []
tabbertabs = []

data = []

def _setuplogging():
	logging.basicConfig(
	filename='parser.log',
	filemode='w',
	format='%(asctime)s [%(levelname)s] %(message)s',
	level=logging.INFO,
	datefmt='[%Y-%m-%d %H:%M:%S]')

def _gethtml():
	req = get(url)
	if req.status_code == 200:
		logging.info('Request sent and object received from [{}]'.format(url))
	else: 
		logging.info('Failed to send request to [{}]'.format(url))
	global page_content
	page_content = req.content
	logging.info('Cleaning up headers, saving content as object {} kilobytes'.format( int((len(page_content)) / 1000) ))

def _soupify():
	global soup
	soup = BeautifulSoup(page_content, "lxml")
	p_title = soup.select_one("head title")
	logging.info('Saving HTML object from page - ["%s"]', p_title.text)

def _grab_headlines():
	global headlines
	tmp_headlines = soup.find_all("span", class_ = "mw-headline")
	for each in tmp_headlines:
		new_headline = each.text.replace(" ", "_").replace("(", "").replace(")", "").lower()
		headlines.append(new_headline)
	tmp_headlines.clear()
	logging.info('Soup found {} mod "headlines" forming a list: {}'.format(len(headlines), headlines))

def _grab_tabbertabs():
	global tabbertabs
	tmp_tabbertabs = soup.find_all("div", class_ = "tabbertab")
	for each in tmp_tabbertabs:
		tabbertabs.append(each['title'].replace(" & ","_").replace(" ","_").replace("slides_","slides").lower())
	logging.info('Soup found {} mod "tabbertabs" forming a list: {}'.format(len(tabbertabs), tabbertabs))

def _grab_display_tables():
	global _list
	_list = soup.find_all('div', attrs = {'style' : 'display:table'})
	if len(_list) > 0: 
		logging.info('Soup found {} objects in list with tag "{}" key: "{}" with value "{}" '.format(len(_list), _list[0].name,
		 next(iter(_list[0].attrs)), _list[0].attrs[next(iter(_list[0].attrs))]))
	elif len(_list) == 0:
		logging.info('Soup found 0 objects in list')

def _fmt(_data, type):
	if type == 'tabber':
		title = _data['title'].replace(" & ","_").replace(" ","_").replace("slides_","slides").lower()
		return title
	elif type == 'effect':
		title = _data.replace("-","").replace("+","").replace("\n","")
		return title
	elif type == 'template':
		title = _data.replace("\n","").replace("\u00a0"," ").replace(" %","").replace(" ","_").replace("/","_").replace("*","").lower()
		return title

def _paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, type):
	td = tmp_td[item_indices.index(key) - 1]
	if len(td.get_text(strip=True)) == 0:
		name_list[name_idx][key] = 0
	else:
		if key == 'magnification':
			name_list[name_idx][key] = _fmt(td.text, 'effect')
		elif key == 'sighting_range':
			name_list[name_idx][key] = eval(type)(_fmt(td.text, 'effect'))
		elif key == 'capacity':
			name_list[name_idx][key] = eval(type)(_fmt(td.text, 'effect'))
		else:
			if td.select_one('font')['color'] == 'green':
				name_list[name_idx][key] = effect_list[0].copy()
				name_list[name_idx][key]['buff'] = eval(type)(_fmt(td.select_one('font').text, 'effect'))
			if td.select_one('font')['color'] == 'red':
				name_list[name_idx][key] = effect_list[1].copy()
				name_list[name_idx][key]['debuff'] = eval(type)(_fmt(td.select_one('font').text, 'effect'))

def _formjson():
	if os.path.exists("./json"):
		if os.path.isfile('./json/mods.json'):
			logging.info("Folder with JSON already exists")
	else:
		os.makedirs("./json")
		logging.info("Folder with JSON created")

	global data

	idx = 0

	for displaytable in _list:
		data.append([headlines[idx]]) # Add to [data] every [] inside of _list [0:[], 1:[], 2:[], 3:[], 4:[]]
		tabber_list = displaytable.find_all("div", class_ = "tabbertab") # Find all <div> tags inside of current displaytable and put inside tabber_list
		
		item_list = []
		tabber_idx = 0
		for tabber in tabber_list: # For each tabber [bipods] ..... [receivers_slides] in tabber_list
			name_list = []
			template = {}
			effect_list = [{"buff" : ""}, {"debuff" : ""}]
			item_list.append([_fmt(tabber, 'tabber')])
			tr_list = tabber.select("tr")
			tmp = tr_list[0]

			th_list = tmp.select("[style='position: sticky;top: 10px;']")

			for column_name in th_list: # Template creation
				template[_fmt(column_name.text, 'template')] = ''	

			item_indices = list(template.keys())
			
			name_idx = 0
			for tr in tr_list[1:]:
				name_list.append(template.copy())
				tmp_td = tr.select('td')
				for key in template:
					if key == "icon": # Always present
						name_list[name_idx]['icon'] = "{}".format(tr.select_one('img')['src'])
					elif key == "name": # Always present
						name_list[name_idx]['name'] = "{}".format(tr.select_one('td a')['title'])
					elif key == "recoil":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'float')
					# elif key == "accuracy":
					# 	_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					elif key == "muzzle_velocity":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'float')
					# elif key == "check_speed_modifier":
					# 	_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					# elif key == "sighting_range":
					# 	_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					# elif key == "ergonomics":
					# 	_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					# elif key == "loudness":
					# 	_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					# elif key == "load_unload_speed_modifier":
					# 	_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					elif key == "capacity":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					elif key == "magnification":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'text')
					else:
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'float')
				name_idx += 1
				# break 
			
			data[idx] = item_list
			data[idx][tabber_idx] = name_list
			tabber_idx += 1
			# break
		idx += 1
		# break

	with open("./json/mods.json", "w") as out:
		ujson.dump(data, out, indent=4, escape_forward_slashes=False) # indent = 4 for pretty output
	logging.info("Rewriting JSON to {}".format(out.name))

if __name__ == "__main__":
	_setuplogging()
	_gethtml()
	_soupify()
	_grab_headlines()
	_grab_tabbertabs()
	_grab_display_tables()
	_formjson()
	# _decompose()