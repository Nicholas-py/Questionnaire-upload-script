from slack_sdk import WebClient
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from selenium import webdriver
from dateutil.parser import parse as dateparse
import base64
import re
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import os
import pathlib
from time import sleep
def pdate(date):
    month = date.strftime("%B")
    day = date.day
    year = date.year
    return f'{day} {month} {year}'

provinces = [
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Nova Scotia",
    "Ontario",
    "Prince Edward Island",
    "Québec",
    "Quebec",
    "Saskatchewan",
    "Northwest Territories",
    "Nunavut",
    "Yukon"
]


#get slack data

slacktoken = input("Enter the bot token (starting with xoxb-): ")
qchannel = 'C087UCJBY82'

dt = dateparse(input('What\'s the date of oldest questionnaire you want to upload? '))
print(f'(Interpreted as {pdate(dt)})')
raw2 = input("Enter the date of the newest questionnaires to upload (optional, if not hit enter)")
if raw2.strip():
    dt2 = dateparse(raw2)
    print(f'(Interpreted as {pdate(dt2)})')
else:
    dt2 = datetime.today()

client = WebClient(token = slacktoken)

def getqs():
    response = client.conversations_history(
        channel=qchannel,
        limit=999,
        oldest=dt.timestamp(),
        latest= dt2.timestamp()
    )

    messages = response.data['messages']
    print('There have been', len(messages),'since',pdate(dt))
    #ts = ((messages[-1]['ts']))  
    #print(datetime.fromtimestamp(float(ts)))

    questionnaires = []
    reacts = set()

    for i1,message in enumerate((messages[::-1])):
        complete = False
        if 'reactions' in message:
            for reaction in message['reactions']:
                reacts.add(reaction['name'])
                if reaction['name'] in ['white_check_mark','x']:
                    #print(f'➖ - #{i1+1}, {pdate(datetime.fromtimestamp(float(message['ts'])))} - already completed')
                    complete = True
        if complete:
            continue
        
        #99% of these are <@member> has joined the channel, so skip them
        if 'blocks' not in message:
            continue
        if message['text'][0:10] != 'A member s':
            continue
        
        try:
            lst = (message['blocks'][1]['text']['text'].split('\n:page_facing_up: <https://coralhealth.app/members/'))
        except:
            print(message['text'])
        memid = lst[0].split('\n:bust_in_silhouette: <https://coralhealth.app/members/')[1].split('|*')[0]
        if memid == 'd631344d-1fd8-4400-9a66-2d32096fb598':
            continue
        responseid = lst[1].split('responses/')[1].split('|*R')[0]
        date = datetime.fromtimestamp(float(message['ts']))
        questionnaires.append((i1+1,date,memid,responseid))




    return questionnaires

questionnaires = getqs()
print('Found', len(questionnaires),'questionnaires uncompleted. Preparing...')

print("Would you like to enter questionnaires into a single MYLE (old) or three different depending on province (new)? ")
inp = input('[Enter 1 or 3] ')
while ('1' not in inp and '3' not in inp) or ('1' in inp and '3' in inp):
    inp = input('[Enter 1 or 3] ')
threemyles = '3' in inp

print()




#log into myle+coral
driver = webdriver.Chrome()
driver.implicitly_wait(2)
driver.get('https://coralhealth.app')

lgin = driver.find_element(By.CLASS_NAME, "MuiButton-root.MuiButton-variantOutlined.MuiButton-colorPrimary.MuiButton-sizeLg.css-1b5vi3t")
lgin.click()
coralwindow = driver.current_window_handle

input("Please log into Coral in the popup. [enter to continue]")

driver.switch_to.new_window('tab')
driver.get('https://coralhealth.medfarsolutions.com/html5/calendar')
mylewindow = driver.current_window_handle

input("Please log into MYLE in the popup. [enter to continue]")

if threemyles:
    driver.switch_to.new_window('tab')
    driver.get('https://coralhealthon.medfarsolutions.com/html5/calendar')
    mylewindowon = driver.current_window_handle
    input("Please log into MYLE Ontario in the popup. [enter to continue]")
    driver.switch_to.new_window('tab')
    driver.get('https://coralhealthbc.medfarsolutions.com/html5/calendar')
    mylewindowbc = driver.current_window_handle
    input("Please log into MYLE BC in the popup. [enter to continue]")


files = []

def savepage(driver, filename):
    # may need to use a driver.wait here
    pdf = driver.execute_cdp_cmd("Page.printToPDF",{})
    with open(filename, "wb") as f:
        f.write(base64.b64decode(pdf["data"]))
        return os.path.abspath(f.name)


#run through - upload questionnaires + print output
def uploadquestionnaire(date, memberid, responseid, manual=False):

    #open member page, get name + prescribers
    driver.switch_to.window(coralwindow)
    driver.get('https://coralhealth.app/members/'+memberid)
    
    failed = True
    nurse = None
    prescriber = None
    for i in range(5):
        try:
            name = driver.find_element(By.CSS_SELECTOR,"div.MuiStack-root p.MuiTypography-root").text
            failed = False
            nurse = driver.find_element(By.XPATH,"//p[normalize-space()='Nurse']/following-sibling::div//p[contains(@class, 'MuiTypography-body-md')]").text
            prescriber = driver.find_element(By.XPATH,"//p[normalize-space()='Prescriber']/following-sibling::div//p[contains(@class, 'MuiTypography-body-md')]").text
            if name == 'undefined undefined' or ' ' not in nurse or ' ' not in prescriber:
                failed = True
                continue
            break
        except WebDriverException:
            pass
    if failed:
        raise Exception("could not obtain name information")
    #print('name:',name, 'nurse:',nurse, 'prescriber:',prescriber)
    try:

        province = driver.find_element(By.XPATH,"//p[" + " or ".join(f"normalize-space(text())='{p}'" for p in provinces) + "]").text
    except:
        raise Exception('Province not found')

    if threemyles:
        if province == 'Quebec':
            currentmyle = mylewindow
        elif province == 'British Columbia':
            currentmyle = mylewindowbc
        else:
            currentmyle = mylewindowon
    else:
        currentmyle = mylewindow
    #open questionnaire
    driver.get('https://coralhealth.app/members/'+memberid+'/questionnaire/responses/'+responseid)

    failed = True
    for i in range(3):
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text
            failed = False
            break
        except WebDriverException:
            pass
    if failed:
        raise Exception("could not get questionnaire")

    titletotype = {
                'Suivi des symptômes et effets secondaires':'ST',
                'Symptom tracker':'ST',
                'Symptom and side effects tracker':'ST',
                'Suivi des symptômes':'ST',
                'GAD-7':'GAD-7',
                'GAD-7 questionnaire':'GAD-7',
                'questionnaire GAD-7':'GAD-7',
                'Résultats du GAD-7':'GAD-7',
                'PHQ-9':'PHQ-9',
                'PHQ-9 questionnaire':'PHQ-9',
                'Résultats du PHQ-9':'PHQ-9',
                'Blood pressure reading':'BP',
                'Lecture de la pression artérielle':'BP',
                'Decreased sexual desire screener (HSDD assessment)':'DSDS',
                'Évaluateur de la diminution du désir sexuel (DSDS)':'DSDS',
                'Rapport taille/hauteur IMC':'RT-IMC',
                'Waist to height ratio and BMI':'WHR-BMI',
                }
    try:
        qtype = titletotype[title]
    except:
        raise KeyError("Questionnaire name "+title+" not known")

    nicedate = pdate(date)
    acronym = ''.join([i[0] for i in name.split(' ')]).upper()
    filename = f'{acronym}_{qtype}_{date.strftime("%b")}{date.day}.pdf'

    mylename = f'{qtype} - {nicedate}'
    #print(filename,mylename)
    abspath = savepage(driver, filename)
    files.append(abspath)



    driver.switch_to.window(currentmyle)


    driver.find_element(By.CLASS_NAME,'CalendarMenuLabel').find_element(By.TAG_NAME,'a').click()

    search = driver.find_element(By.ID,'__patientSearchField')
    search.send_keys(Keys.CONTROL + "a")
    search.send_keys(Keys.DELETE)
    driver.implicitly_wait(0)
    try:
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, 'sidebar-item')) == 0
        )
    except:
        raise Exception("Searching failed")
    driver.implicitly_wait(2)

    searchname = name.split(' ')[0] + ' '+ name.split(' ')[-1]

    search.send_keys(searchname)

    if manual:
        input('Please enter the member page for member '+name+', then hit enter.')
    else:
        patients = driver.find_elements(By.CLASS_NAME, 'sidebar-item')
        if len(patients) < 1:
            raise Exception("No MYLE profile with this name found")
        if len(patients) > 1:
            raise Exception("Two MYLE profiles with this name found")
        assert len(patients) == 1
        patients[0].click()


    driver.implicitly_wait(0.4)
    try:
        driver.find_element(By.ID,'__okButton').click()
    except:
        pass
    driver.implicitly_wait(2)

    docbutton = driver.find_element(By.XPATH, "//a[@title='Received Documents']")
    driver.execute_script("arguments[0].click();", docbutton)

    driver.find_element(By.XPATH, "//a[@data-cy='document-allDocuments']").click()

    driver.find_element(By.CLASS_NAME,'displaced-nav-btns').find_element(By.TAG_NAME,'a').click()

    driver.find_element(By.XPATH,'//*[@data-cy=\'document-addDoc-source\']').send_keys('Membre - Coral App')
    for medteam in [nurse, prescriber]:
        if medteam is None:
            continue
        bestword = max(re.split(r'[-\s]+',medteam),key=len)

        driver.find_element(By.ID, 'input_add_doc_clinicians').send_keys(medteam)
        bestword = bestword.lower()
        for i,l in enumerate('àâäçéèêëîïôöùûüÿ'):
            bestword = bestword.replace(l, 'aaaceeeeiioouuuy'[i])

        #print(bestword)
        try:
            dropdown = driver.find_element(By.XPATH,f"//li[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸàâäçéèêëîïôöùûüÿ', 'abcdefghijklmnopqrstuvwxyzaaaceeeeiioouuuyaaaceeeeiioouuuy'), '{bestword}')]]")
        except:
            continue
        driver.execute_script("arguments[0].click();", dropdown)

    driver.find_element(By.XPATH,'//*[@data-cy=\'document-addDoc-description\']').send_keys(mylename)
    dateelem = driver.find_element(By.ID, 'doc_create_date')
    for _ in range(35):
        dateelem.send_keys(Keys.BACKSPACE)
    #print(f'{date.strftime('%A')}, {nicedate}')
    dateelem.send_keys(f'{date.strftime('%A')}, {nicedate}')
    dateelem.send_keys(Keys.ENTER)

    driver.find_element("xpath", "//input[@type='file']").send_keys(abspath)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@data-cy='document-addDoc-attach']"))
    ).click()

    for i in range(10):
        try:
            path = pathlib.Path(abspath)
            path.unlink()
            files.remove(abspath)
            break
        except PermissionError:
            sleep(0.2)
    else:
        print('Delete failed')


    with open('QuestionnairesUploaded.txt','a+') as file:
        file.write(f'member:{memberid}; questionnaire:{responseid}; upload date:{datetime.today().strftime('%Y-%m-%d')}; province:{province}\n')

    response = client.reactions_add(channel=qchannel,name='white_check_mark',timestamp=date.timestamp())
    #print(response)
    if not response['ok']:
        print('Reaction adding failed.')
    return 'success', province

def gothrough(questionnaires, manual=False):
    failures = []
    for i, date, memberid, responseid in questionnaires:
        try:
            result, province = uploadquestionnaire(date, memberid, responseid,manual)
            print(f'✅ - #{i}, member {memberid} on {pdate(date)} in {province}')
        except (Exception, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                print('\n\n\nDeleting leftover files...')
                for abspath in files:
                    path = pathlib.Path(abspath)
                    path.unlink()
                    files.remove(abspath)
                return

            if isinstance(e, WebDriverException):
                if '::' in e.msg:
                    reason = e.msg.split('\n')[0].split('::')[1]
                else:
                    reason = e.msg.split('\n')[0]
            else:
                reason = str(e)
            print(f'❌ - #{i}, member {memberid} on {pdate(date)} (reason - {reason})')
            failures.append((i,date,memberid, responseid))

    for abspath in files:
        path = pathlib.Path(abspath)
        path.unlink()
        files.remove(abspath)
    return failures

while True:
    manual = 'y' in input('Would you like to enter member\'s names manually? (Use this if you got a "no/two member(s) with this name found" error last time) ')
    print()
    if manual:
        print("You are in manual mode. When searching MYLE, the script will pause and wait for you to enter the page of the correct member. If there are two with the same name, check the Coral tab to find the birthdate and find the correct member based on that. When finished, return to the script and hit enter.")
        input('[enter to continue]')


    failures = gothrough(questionnaires, manual)


    print('Finished! ')
    print(f'There were {len(failures)} failures (/{len(questionnaires)})')
    print('If some failed, run the script again (possibly in manual mode) or message Nicholas Waslander for assistance.')
    print('To mark a questionnaire not to be completed by the bot, react :x: to it on slack.')

    print()
    if 'y' not in input('Would you like to run the script again? '):
        break

    questionnaires = getqs()

    print('Found', len(questionnaires),'questionnaires uncompleted.')



print('Make sure to double-check there are no downloaded PDFs remaining on your device.')
print('To see a list of the questionnaires uploaded, look at QuestionnairesUploaded.txt')
