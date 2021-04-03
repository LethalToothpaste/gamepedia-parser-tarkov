from bs4 import BeautifulSoup # Импортируем модуль парсера HTML -> Python объекты
from requests import get # Подмодуль из request для get реквестов
import logging # Логирование 
import ujson # Улучшенный модуль для работы с JSON
import os # Дефолтные функции для работы с осью, создание и запись в файл
import collections # Модуль работы с словарями
# from decomposer import _decompose # Мой модуль для разбивки огромного объекта JS на категории #DEPRECIATED

# Создаем список URLов для GET запросов, пока что код использует первый для сбора данных о модах
url = ["https://escapefromtarkov.gamepedia.com/Weapon_mods"]


# Декларируем списки для работы парсера
headlines = [] # Список будет содержать названия категорий модов [Functional Mods, Muzzle Devices, Sights, Gear Mods, Vital parts]
tabbertabs = [] # Список будет содержать названия под-категории [Bipods, Foregrips...] для каждой категории выше

data = [] # Список в котором будет храниться ВЕСЬ объект с всеми данными и который передаем кодировщику ujson 

# Настройка логера на уровень INFO, выдает лог в файл parser.log в корневой папке, вызывается под блоком функций для дебага
def _setuplogging():
	logging.basicConfig(
	filename='parser.log',
	filemode='w',
	format='%(asctime)s [%(levelname)s] %(message)s',
	level=logging.INFO,
	datefmt='[%Y-%m-%d %H:%M:%S]')

# Функция вызывает метод GET из Requests по ссылке из списка https:// ... Weapon_mods
def _gethtml(url):
	req = get(url) # Отправляем GET на сервер и получаем ответ
	if req.status_code == 200: # Если код ответа 200 - все успешно получено
		logging.info('Request sent and object received from [{}]'.format(url))
	else: 
		logging.info('Failed to send request to [{}]'.format(url)) # Иначе ошибка в логер
	global page_content # Глобалим объект для хранения, сейчас он пустой
	page_content = req.content # Присваиваем объекту контент страницы вырезая хедеры и другой мусор, оставляя <body></body>
	logging.info('Cleaning up headers, saving content as object {} kilobytes' # Логируем общий объем полученных данных
	.format( int((len(page_content)) / 1000) ))

def _soupify(): # Функция обработки HTML контента и конверсии в объекты питона
	global soup # Глобалим объект в котором хранится обработанный объект (уже питоновский)
	soup = BeautifulSoup(page_content, "lxml") # Приравниваем объект обработанному парсером BSoup контент с парсером lxml
	# lxml - самый быстрый и подходящий на данный момент, больше инфы на https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser
	p_title = soup.select_one("head title") # Находим в объекте тэг с названием страницы для логера (это неважно для работы)
	logging.info('Saving HTML object from page - ["%s"]', p_title.text) # Выводим название страницы для логера (это неважно для работы)

def _grab_headlines(): # Собираем названия категорий модов, их всего пока что 5
	global headlines # Глобалим объект с названиями, пока он пуст
	tmp_headlines = soup.find_all("span", class_ = "mw-headline") # Находим все тэги <span> с классом "mw-headline"
	for each in tmp_headlines: # Итерация через все найденные <span>
		new_headline = each.text.replace(" ", "_").replace("(", "").replace(")", "").lower() # Форматируем названия в лоуеркейс и убираем пробелы
		headlines.append(new_headline) # Добавляем в список каждый из новых категорий
	tmp_headlines.clear() # Чистим временный список после работы с ним, данные уже переведены в основной список
	logging.info('Soup found {} mod "headlines" forming a list: {}'.format(len(headlines), headlines)) # Логирование списка

def _grab_tabbertabs(): # Собираем названия подкатегорий
	global tabbertabs # Глобалим список подкатегорий
	tmp_tabbertabs = soup.find_all("div", class_ = "tabbertab") # Находим все тэги <div> с классом "tabbertab"
	for each in tmp_tabbertabs: # Итерация через все найденные <div>
		tabbertabs.append(each['title'].replace(" & ","_") # Форматируем и пишем в список каждую подкатегорию
		.replace(" ","_").replace("slides_","slides").lower())
	logging.info('Soup found {} mod "tabbertabs" forming a list: {}'.format(len(tabbertabs), tabbertabs)) # Логирование подкатегорий

def _grab_display_tables(): # Собираем все display:table они соответсвуют названию категории содержащие все подкатегории
	global _list # Глобалим список "дисплеев"
	_list = soup.find_all('div', attrs = {'style' : 'display:table'}) # Находим все <div> с классом "display:table"
	if len(_list) > 0: # Если список не пуст - выводим с форматированием его в логер
		logging.info('Soup found {} objects in list with tag "{}" key: "{}" with value "{}" '.format(len(_list), _list[0].name,
		 next(iter(_list[0].attrs)), _list[0].attrs[next(iter(_list[0].attrs))])) # Я если честно не помню че это ХАХАХАХХ на ревью разберем
	elif len(_list) == 0: # Если список пустой выводим это в логер
		logging.info('Soup found 0 objects in list')

def _fmt(_data, type): # Форматирование строки, берет аргумент для выбора вида форматирования
	if type == 'tabber': # Если табер меняем все символы на пробелы, slides_ это фикс одной строки
		title = _data['title'].replace(" & ","_").replace(" ","_").replace("slides_","slides").lower()
		return title
	elif type == 'effect': # Если это эффект убираем + - и переход на новую строку html
		title = _data.replace("-","").replace("+","").replace("\n","")
		return title
	elif type == 'template': # Если это шаблон то форматируем текст под нужный нам вид
		title = _data.replace("\n","").replace("\u00a0"," ").replace(" %","").replace(" ","_").replace("/","_").replace("*","").lower()
		return title

def _paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, type): # Функция сборки 
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
					elif key == "muzzle_velocity":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'float')
					elif key == "capacity":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'int')
					elif key == "magnification":
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'text')
					else:
						_paste_data(tmp_td, item_indices, key, name_list, effect_list, name_idx, 'float')
				name_idx += 1
			
			data[idx] = item_list
			data[idx][tabber_idx] = name_list
			tabber_idx += 1
		idx += 1

	with open("./json/mods.json", "w") as out:
		ujson.dump(data, out, indent=4, escape_forward_slashes=False) # indent = 4 for pretty output
	logging.info("Rewriting JSON to {}".format(out.name))

if __name__ == "__main__":
	_setuplogging()
	_gethtml(url[0])
	_soupify()
	_grab_headlines()
	_grab_tabbertabs()
	_grab_display_tables()
	_formjson()
	# _decompose()