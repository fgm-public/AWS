
# This function analyzes vacancies from the database (MongoDB),
# generates xlsx report and upload it to the AWS S3 Storage.
# Then adds xlsx report public hyperlink to the database (MongoDB).
# This is LOCAL version, intended fot testing purposes only!

# Output stream for saving report files:
from io import BytesIO
# Regular expressions:
from re import sub, findall
# Some stuff to deserialize objects:
from json import loads, dumps
# For xlsx reports creation:
from pandas import DataFrame, ExcelWriter
# MongoDB driver:
from pymongo import MongoClient
# Our MongoDB connection class:
from mongocon import MongoConnection
# Some mathematics:
from statistics import median
# Count items:
from collections import Counter
# HTML parsing:
from bs4 import BeautifulSoup
# Some filter vocabulary
from filtervocabulary import vocabulary
# And finally, our credentials:
from credentials import s3, mongo, sqs


class VacancyAnalyzer:
    ''' Сlass is designed to analyze information about vacancies'''

#---------------------------------------------------------------------------------------------------------
#---Initializations---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    def __init__(self): ##, occupation):

        # Full vacancies batch itself
        self.vacancies = None

        # Occupation name
        ##self.occupation = occupation
        self.occupation = None

        # s3 public hyperlink to xlsx report
        self.report_url = None
        
        # Names of all vacancies in batch
        self.vacancy_names = None

        # Keyskills (tags) top and all
        self.skills = None
        self.skills_all = None
 
        # Keywords (all english words) top and all
        self.keywords = None
        self.keywords_all = None

        # All subject headings (html 'strongs') from vacancy descriptions
        self.description_sections = None

        # Child elements from all subject headings (html 'strongs')
        self.description_elements_all = None

        # Child elements from top 10 subject headings (html 'strongs')
        self.description_elements = None

        # Child elements from description_sections_top subject headings (html 'strongs')
        self.description_elements_top = None

        # Wordbags formed from self.description_elements
        self.wordbags_all = None
        
        # Wordbags formed from self.description_sections_top
        self.wordbags = None
        
        # Common professional areas in retrieved vacancies
        self.profareas = None
        
        # Specialization areas in retrieved vacancies
        self.profareas_granular = None
        
        # Publication dates
        self.dates = None
        
        # Regions
        self.regions = None
        
        # Required experience
        self.experience = None

        # Employers list with full info: id, vacancies url . . .
        self.employers_full = None
        # Employers list in {name:url} format
        self.employers_brief = None
        
        # Number of unique vacancies among all
        self.unique = None
        
        # HH clusters of vacancies
        self.clusters = None

        # Average salary
        self.average_salary = 0

        # Median salary
        self.median_salary = 0

        # Modal salary
        self.modal_salary = 0

        # Salary groups
        self.salary_groups = {
            'Менее 20000' : 0,
            '20000-30000' : 0,
            '30000-40000' : 0,
            '40000-50000' : 0,
            '50000-60000' : 0,
            '60000-70000' : 0,
            '70000-90000' : 0,
            'Более 90000' : 0
            }

        # Top of 'strong's' dictionary corpus,
        # formed from lots of batches of different vacancies retrieved previously
        self.description_sections_top = frozenset({
            'Требования',
            'Обязанности',
            'Условия',
            'Мы предлагаем',
        })

    def __len__(self):
        return len(self.vacancies)

    def __getitem__(self, position):
        return self.vacancies[position]

    def __repr__(self):
        return (f"Totally {self.__len__()} vacancies on "
        f"'{self.occupation}' occupation")


#---------------------------------------------------------------------------------------------------------
#---Public service methods--------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # This function deletes a message from the queue,
    # which was sent by the previous lambda function.
    #---------------------------------------------------------------------------------------------------------
    def delete_message_from_queue(self):
        # Receive message and provide 'VisibilityTimeout' to queue
        raw_message = sqs.receive_message(QueueUrl=incoming_queue,
                                          VisibilityTimeout=60)
        # Receive 'ReceiptHandle' from message
        receipt_handle = raw_message['Messages'][0]['ReceiptHandle']
        # And finally deletes the message
        sqs.delete_message(QueueUrl=incoming_queue,
                           ReceiptHandle=receipt_handle)

    # This function queues a message to wake up the next lambda.
    #---------------------------------------------------------------------------------------------------------
    def add_message_to_queue(self):
        # Create message (dict object)
        raw_message = {"Wake": 'Up'}
        # Serialize message object, because queue requires string messages
        message = dumps(raw_message)
        # Put it to queue
        sqs.send_message(
                QueueUrl=outgoing_queue,
                MessageBody=message,
            )

    # This function gets an occupation name from MongoDB to request it from HH API.
    #---------------------------------------------------------------------------------------------------------
    def get_occupation_from_mongo(self):
        # MongoDB connection object    
        client = MongoConnection()
        # Use our connection object with context manager to handle connection
        with client:
            # Connection to 'orders' collection of 'hh_reports' database
            collection = client.connection.hh_reports['orders']
            # Get number of last added order
            number = collection.estimated_document_count()-1
            # Get occupation name
            raw_document = collection.find().skip(number)
            occupation = raw_document[0].get('occupation')
            self.occupation = occupation

    # This function gets vacancies from MongoDB
    #---------------------------------------------------------------------------------------------------------
    def get_vacancies_from_mongo(self):
        # MongoDB connection object    
        client = MongoConnection()
        # Use our connection object with context manager to handle connection
        with client:
            # Connection to 'orders' collection of 'hh_reports' database
            collection = client.connection.hh_vacancies[self.occupation]
            self.vacancies = [document
                for document in collection.find({})]

    # This function stores analyze result into xlsx file,
    # then stores this file in AWS S3 object storage.
    #---------------------------------------------------------------------------------------------------------
    def store_report_to_s3(self):

        def form_sheet(data, columns, name):
            # Defines sheet structure
            sheet = DataFrame(data, columns=columns)
            # Add sheet to xlsx document
            sheet.to_excel(writer, name, index=False)
        
        # Xlsx file structure
        table_structure = {
            'Должности': ['Название должности', 'Количество вакансий'],
            'Ключевые навыки': ['Ключевые навыки (тэги)', 'Вакансий'],
            'Опыт': ['Требуемый опыт', 'Вакансий'],        
            'Технологии': ['Продукты|Технологии', 'Вакансий'],        
            'Работодатели': ['Работодатель', 'Ссылка'],
            'Регионы': ['Регион', 'Вакансий'],
            'Профобласти': ['Профобласть', 'Вакансий'],
            'Специализации': ['Специализация', 'Вакансий'],
            'Группы': ['Диапазон', 'Вакансий'],
            'Зарплата': ['Средняя зарплата', 'Медианная зарплата', 'Модальная зарплата'],
        }
        
        # Defines output stream
        output = BytesIO() #
        # Defines pandas xlsx writer and saves xlsx file into output stream
        with ExcelWriter(output) as writer:

            form_sheet(self.vacancy_names, table_structure['Должности'], 'Должности')
            form_sheet(self.skills_all, table_structure['Ключевые навыки'],'Ключевые навыки')
            form_sheet(self.keywords_all, table_structure['Технологии'], 'Технологии')
            form_sheet(self.regions, table_structure['Регионы'], 'Регионы')
            form_sheet(self.experience, table_structure['Опыт'], 'Опыт')
            form_sheet(self.employers_brief.items(), table_structure['Работодатели'], 'Работодатели')
            form_sheet(self.profareas, table_structure['Профобласти'], 'Профобласти')
            form_sheet(self.profareas_granular, table_structure['Специализации'], 'Специализации')
            form_sheet(self.salary_groups.items(), table_structure['Группы'], 'Зарплатные группы')
            form_sheet([(self.average_salary, self.median_salary, self.modal_salary),],
                    table_structure['Зарплата'], 'Зарплата')

            for criteria in vocabulary['Знания']:
                form_sheet(set(self._by_word_extractor(criteria)),
                        [criteria.capitalize()],
                        criteria.capitalize())

            for criteria in self.description_elements_top:
                form_sheet(set(self.description_elements_top.get(criteria)),
                        [criteria.capitalize()],
                        criteria.capitalize())
            
            form_sheet(self.wordbags_all, ['Слово', 'Вхождений'], 'Мешок слов')

        # Put file content into 'data'
        data = output.getvalue() #

        s3.put_object(ACL='public-read',
                      Body=data,
                      Bucket='xlsx-reports',
                      Key=f'{self.occupation}.xlsx')

        # Old path-style model (region specific) url:
        ##location = s3.get_bucket_location(Bucket='xlsx-reports')['LocationConstraint']
        ##self.report_url = f"https://s3-{location}.amazonaws.com/xlsx-reports/{self.occupation}.xlsx"
        
        # New virtual-hosted style S3 url:
        self.report_url = (f"https://xlsx-reports.s3.amazonaws.com/"
                           f"{self.occupation}.xlsx")


    # This function stores xlsx report hyperlink into mongo
    #---------------------------------------------------------------------------------------------------------
    def add_href_to_mongo(self):
        # MongoDB connection object    
        client = MongoConnection()
        # Use our connection object with context manager to handle connection
        with client:
            # Connection to 'xlsx' collection of 'hh_reports' database
            collection = client.connection.hh_reports['xlsx']
        
            occupations = [document.get('occupation')
                for document in collection.find()]
            
            if self.occupation not in occupations:
                collection.insert({'occupation': self.occupation,
                                'report': self.report_url})

#---------------------------------------------------------------------------------------------------------
#---Analyze-----------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Call all analyze methods                        
    def analyze(self):

        self._duplicate_vacancies_remover()
        self._skills_collector()
        self._experience_collector()
        self._prof_areas_collector()
        self._creation_dates_collector()
        self._vacancy_names_collector()
        self._regions_collector()
        self._keywords_extractor()
        self._description_elements_extractor()
        self._description_sections_extractor()
        self._wordbags_extractor()
        self._unique_counter()
        self._salary_calculator()
        self._employers_collector()

#---------------------------------------------------------------------------------------------------------
#---Collectors--------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Collect key skills
    #---------------------------------------------------------------------------------------------------------
    def _skills_collector(self):
        
        raw_key_skills = [vacancy.get('key_skills')
            for vacancy in self.vacancies]

        # Cleaning skills
        mixed_key_skills = [key_skill.get('name')
            for item in raw_key_skills
                for key_skill in item]

        # Forms {key_skill : number of entries}
        key_skills_counted = {skill : mixed_key_skills.count(skill)
            for skill in mixed_key_skills}

        # Forms {key_skill : number of entries}
        ##key_skills_counted = {}
        ##for skill in mixed_key_skills:
        ##    key_skills_counted[skill] = key_skills_counted.get(skill, 0) + 1

        # Sort by number of entries
        self.skills_all = sorted(key_skills_counted.items(),
                                 key=lambda x: x[1],
                                 reverse=True)
        
        self.skills = self.skills_all[0:100]


    # Collect required work experience from vacancies
    #---------------------------------------------------------------------------------------------------------
    def _experience_collector(self):

        raw_experience = [full_vacancy.get('experience').get('name')
            for full_vacancy in self.vacancies]
        
        # Forms {experience : number of entries}
        experience = {exp : raw_experience.count(exp)
            for exp in raw_experience}
        
        # Sort by number of entries
        self.experience = sorted(experience.items(),
                                 key=lambda x: x[1],
                                 reverse=True)


    # Collect vacancy names
    #---------------------------------------------------------------------------------------------------------
    def _vacancy_names_collector(self):

        vacancy_names = [vacancy.get('name').lower()
            for vacancy in self.vacancies]
        
        # Forms {vacancy name : number of entries}
        vacancy_names_counted = {name.capitalize() : vacancy_names.count(name)
            for name in vacancy_names}
        
        # Sort by number of entries
        self.vacancy_names = sorted(vacancy_names_counted.items(),
                                    key=lambda x: x[1],
                                    reverse=True)


    # Collect specialization areas from vacancies
    #---------------------------------------------------------------------------------------------------------
    def _prof_areas_collector(self):

        ##raw_area_ids = [categories.get('id')
        ##   for raw_specialization in raw_specializations
        ##      for categories in raw_specialization]
        ##raw_areas = {categories.get('profarea_name') : categories.get('name')
        ##    for raw_specialization in raw_specializations
        ##        for categories in raw_specialization}
        ##Forms {experience : number of entries}
        ##areas = {id : raw_area_ids.count(id)
        ##    for id in raw_area_ids}

        raw_specializations = [full_vacancy.get('specializations')
            for full_vacancy in self.vacancies]
        
        specializations = [vacancy_specializations
            for vacancy_specializations_list in raw_specializations
                for vacancy_specializations in vacancy_specializations_list]
        
        profareas = [key['profarea_name']
            for key in specializations]
        
        profareas_granular = [key['name']
            for key in specializations]
        
        # Forms {profarea : number of entries}
        profareas_counted = {profarea : profareas.count(profarea)
            for profarea in profareas}
        
        # Forms {granular profarea : number of entries}        
        profareas_granular_counted = {profarea : profareas_granular.count(profarea)
            for profarea in profareas_granular}

        # Sort by number of entries
        self.profareas = sorted(profareas_counted.items(),
                                key=lambda x: x[1],
                                reverse=True)

        # Sort by number of entries        
        self.profareas_granular = sorted(profareas_granular_counted.items(),
                                         key=lambda x: x[1],
                                         reverse=True)

    
    # Collect creation dates from vacancies
    #---------------------------------------------------------------------------------------------------------
    def _creation_dates_collector(self):

        raw_create_dates = [vacancy.get('created_at')
            for vacancy in self.vacancies]
        
        # Sort by date of publication
        self.dates = sorted({date : raw_create_dates.count(date)
            for date in raw_create_dates})

    
    # Collect employers
    #---------------------------------------------------------------------------------------------------------
    def _employers_collector(self):

        self.employers_full = [vacancy.get('employer')
            for vacancy in self.vacancies]

        self.employers_brief = {vacancy.get('employer').get('name'):
                                vacancy.get('employer').get('alternate_url')
            for vacancy in self.vacancies}


    # Collect regions
    #---------------------------------------------------------------------------------------------------------
    def _regions_collector(self):

        regions = [vacancy.get('area').get('name')
            for vacancy in self.vacancies]

        # Forms {regions : number of entries}
        regions_counted = {region : regions.count(region)
            for region in regions}
        
        # Sort by number of entries
        self.regions = sorted(regions_counted.items(),
                                    key=lambda x: x[1],
                                    reverse=True)


#---------------------------------------------------------------------------------------------------------
#---Extractors--------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Wordbags formed from self.description_sections_top, which in turn is
    # Top of 'strong's' dictionary formed from lots of batches of different vacancies
    #---------------------------------------------------------------------------------------------------------
    def _wordbags_extractor(self):

        def extract_by_criteria(criteria):
            
            if self.description_elements.get(criteria):
                clear_strings = [sub("[^А-Яа-я0-9-.\s]", "",
                                     describe_string.lower().strip().strip('.'))
                    for describe_string in self.description_elements.get(criteria)]

                unique_clear_set = set(clear_strings)
                unique_strings = [str(string)
                    for string in unique_clear_set]

                ##unique_strings = sorted(unique_strings, key=len)
                bags_words = [Counter(findall(r'\w+', string))
                    for string in unique_strings]

                bag_words = sum(bags_words, Counter())
                sorted_bag = sorted(bag_words.items(),
                                    key=lambda x: x[1],
                                    reverse=True)
                result = [word for word in sorted_bag
                    if len(word[0]) > 4]

                return result
        
        self.wordbags = {criteria : extract_by_criteria(criteria)
            for criteria in self.description_sections_top}
        
        all_words_in_string = ' '.join(self.description_elements_all)    
        bags_words = Counter(findall(r'\w+', all_words_in_string))
        self.wordbags_all = sorted(bags_words.items(),
                                   key=lambda x: x[1],
                                   reverse=True)

    # Extract all english words from vacancy desriptions
    #---------------------------------------------------------------------------------------------------------
    def _keywords_extractor(self):

        # Texts list from vacancy descriptions
        descriptions = [BeautifulSoup(vacancy.get('description'), 'html.parser').get_text()
            for vacancy in self.vacancies]

        # Extract english words
        raw_eng_extraxtions = [sub("[^A-Za-z]", " ", description.strip())
            for description in descriptions]
        
        # Clearing
        raw_eng_words = [raw_eng_extraxtion.split('  ')
            for raw_eng_extraxtion in raw_eng_extraxtions]
        
        eng_words = [words.strip()
            for raw_eng_word in raw_eng_words
                for words in raw_eng_word
                    if words != '']
        
        clear_eng_words = list(filter(None, eng_words))
        eng_words_mixed = {word : clear_eng_words.count(word)
            for word in clear_eng_words}

        # Sorted by number of entries
        self.keywords_all = sorted(eng_words_mixed.items(),
                                   key=lambda x: x[1],
                                   reverse=True)
        self.keywords = self.keywords_all[0:100]


    # Extract child elements from all subject headings (html 'strongs')
    #---------------------------------------------------------------------------------------------------------
    def _description_elements_extractor(self):

        # bs4.BeautifulSoup objects list formed from vacancy descriptions
        vacancy_descriptions = [BeautifulSoup(vacancy.get('description'), 'html.parser')
            for vacancy in self.vacancies]
        
        p_tags = [p.text.strip().lower()
            for soup in vacancy_descriptions
                for p in soup.find_all('p')]
        li_tags = [li.text.strip().lower()
            for soup in vacancy_descriptions
                for li in soup.find_all('li')]
        
        self.description_elements_all = list(set(p_tags + li_tags))

    
    # Extract multiple different things from vacancy description bodies
    #---------------------------------------------------------------------------------------------------------
    def _description_sections_extractor(self):

        # bs4.BeautifulSoup objects list formed from vacancy descriptions
        description_soups = [BeautifulSoup(vacancy.get('description'), 'html.parser')
            for vacancy in self.vacancies]
        
        # Vacancy descriptions sections list grouped by vacancy framed into <strong> tags
        strong_soups = [description_soup.findAll('strong')
            for description_soup in description_soups]

        # All vacancy descriptions sections from all vacancies in common list
        strongs = [strong.text
            for strong_soup in strong_soups
                for strong in strong_soup]

        # Clearing
        clear_strongs = [sub("[^А-Яа-я\s]", "", strong.strip())
            for strong in strongs]

        clear_strongs = list(filter(None, clear_strongs))
        clear_strongs = list(filter(lambda x: x!=' ', clear_strongs))

        ##self.description_sections = clear_strongs

        # Forms {strong : number of entries}
        strongs_counted = {strong : clear_strongs.count(strong)
            for strong in clear_strongs}

        # Sort by number of entries
        sorted_strongs = sorted(strongs_counted.items(),
                                key=lambda x: x[1],
                                reverse=True)
        
        self.description_sections = sorted([strong[0]
            for strong in sorted_strongs], key=len, reverse=True)
        
        strong_top = [strong[0]
            for strong in sorted_strongs[:10]]

        self.description_elements = {key: []
            for key in strong_top}

        self.description_elements_top = {key: []
            for key in self.description_sections_top}

        for description in description_soups:
            strongs = description.findAll('strong')
            for strong in strongs:
                for top in strong_top:
                    if strong.get_text().count(top):
                    ##if len(strong.findNext().findAll('li')) > 0:
                        try:
                            self.description_elements[top] += [item.text
                                for item in strong.findNext().findAll('li')]
                        except AttributeError:
                            pass
                
                for top in self.description_sections_top:
                    if strong.get_text().count(top):
                    ##if len(strong.findNext().findAll('li')) > 0:
                        try:
                            # Suffix '.lstrip().capitalize()' clarifies but slows down
                            self.description_elements_top[top] += [item.text.lstrip().capitalize()
                                for item in strong.findNext().findAll('li')]
                        except AttributeError:
                            pass
        
       
    # Get python list of list 'description_sections_top' filtered by custom 'filter_vocabulary' key
    #---------------------------------------------------------------------------------------------------------

    # Dirty, but fast version
    ##def _by_word_extractor(self, criteria):
    ##    result = [element
    ##        for element in self.description_elements_all
    ##            if criteria in element]
    ##    return sorted(result, key=len)

    # Clear, but slow version
    def _by_word_extractor(self, criteria):
        result = list()   

        for element in self.description_elements_all:
            if criteria in element:
                if element:
                    while element[0].isalpha() == False:
                        element = element.lstrip(element[0])
                        if not element:
                            break
                    result.append(element.capitalize())
        
        return sorted(result, key=len)
        
#---------------------------------------------------------------------------------------------------------
#---Calculators-------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Calculate average, median, modal salaries and group salaries into number of clusters
    #-----------------------------------------------------------------------------------------------------
    def _salary_calculator(self):
        
        def _get_salary_group(salary):
            return {
                salary < 20000: 'Менее 20000',
                20000 <= salary < 30000: '20000-30000',
                30000 <= salary < 40000: '30000-40000',
                40000 <= salary < 50000: '40000-50000',
                50000 <= salary < 60000: '50000-60000',
                60000 <= salary < 70000: '60000-70000',
                70000 <= salary < 90000: '70000-90000',
                90000 <= salary: 'Более 90000'
            }[True]
        
        sum = total = 0
        salary_all = []
    
        regions = [region[0] for region in self.regions]
    
        region_salary_dict = {'average_salary': 0,
                              'median_salary': 0,
                              'modal_salary': 0,
                              'sum': 0,
                              'total': 0,
                              'salary_all': [],
                            }

        self.salaries_by_region = {region: region_salary_dict
            for region in regions}

        for vacancy in self.vacancies:

            region = vacancy.get('area').get('name')

            if vacancy.get('salary'):
                salary = dict(vacancy['salary'])
                if salary.get('currency') == 'RUR':
                    if salary.get('gross'):
                        if salary.get('from'):
                            salary['from'] = salary['from'] * 0.87
                        if salary.get('to'):
                            salary['to'] = salary['to'] * 0.87
                    if salary.get('from'):
                        self.salaries_by_region[region]['sum'] += salary.get('from')
                        self.salaries_by_region[region]['total'] += 1
                        self.salaries_by_region[region]['salary_all'].append(salary.get('from'))
                        self.salary_groups[_get_salary_group(int(salary.get('from')))] += 1
                        salary_all.append(salary.get('from'))
                        sum += salary.get('from')
                        total += 1
                    if salary.get('to'):
                        self.salaries_by_region[region]['sum'] += salary.get('to')
                        self.salaries_by_region[region]['total'] += 1
                        self.salaries_by_region[region]['salary_all'].append(salary.get('to'))                       
                        self.salary_groups[_get_salary_group(int(salary.get('to')))] += 1
                        salary_all.append(salary.get('to'))
                        sum += salary.get('to')
                        total += 1
        
        self.median_salary = median(salary_all)
        
        if total > 0:
            self.average_salary = round(sum/total)

        for region in regions:
            self.salaries_by_region[region]['median_salary'] = \
                median(self.salaries_by_region[region]['salary_all'])

            if self.salaries_by_region[region]['total'] > 0:
                self.salaries_by_region[region]['average_salary'] = \
                    round(self.salaries_by_region[region]['sum'] \
                        / self.salaries_by_region[region]['total'])
        
        # Calculate modal salary
        for group, salary in self.salary_groups.items():
            if salary == max(self.salary_groups.values()):
                self.modal_salary = group

#---------------------------------------------------------------------------------------------------------
#---Misc--------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

    # Remove dubplicates in vacancies list
    #---------------------------------------------------------------------------------------------------------
    def _duplicate_vacancies_remover(self):
        
        unique_vacancies = []

        for vacancy in self.vacancies:
            if vacancy not in unique_vacancies:
                unique_vacancies.append(vacancy)

        self.vacancies = unique_vacancies


    # Count unique vacancies in vacancies list
    #---------------------------------------------------------------------------------------------------------
    def _unique_counter(self):

        self.unique = len({vacancy.get('id')
            for vacancy in self.vacancies})

#---------------------------------------------------------------------------------------------------------
#---Main--------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    
    from vacancy_analyzer import VacancyAnalyzer
    v = VacancyAnalyzer()
    v.delete_message_from_queue()
    v.get_occupation_from_mongo()
    v.get_vacancies_from_mongo()
    v.analyze()
    v.store_report_to_s3()
    v.add_href_to_mongo()
    v.add_message_to_queue()
