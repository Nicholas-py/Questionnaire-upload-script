# Questionnaire-upload-script
This is a script to automatically upload questionnaires from the Coral app to MYLE, using the automated Slack messages as a checklist. If you have any problems/questions, reach out to Nicholas Waslander on Slack or by email at nicholas.waslander@gmail.com. 

## How it works
When the script is run, you provide it a date range. It connects to the Questionnaire Data Bot on Slack, and finds all questionnaire notifications in that range without the ✅ or :x: reaction. It then attempts to upload all of them to MYLE, and reacts with the ✅ to every one it completes.


## Running the script
 1. Download the file CoralQuestionnaireAuto.py (click on it under code, then click download in the top right)
 2. Install [Python](https://www.python.org/downloads/).
 3. Open the command prompt - choose one of the following (windows only):
    * Go to file manager, locate the downloaded file, then click on the status bar at the top and type "cmd"
    * Open command prompt via the start menu, then type cd [path to folder the file is in], ex cd C:\Users\nicholas\Downloads
4. Install packages - selenium, slack_sdk, pathlib.
    * In the command prompt, type `pip install selenium` and hit enter. Wait for the install to finish, then repeat with `pip install slack_sdk` and `pip install pathlib`
5. Run "python CoralQuestionnaireAuto.py" (or, if you renamed the file, change CoralQuestionnaireAuto to the new filename).
6. Paste the slack token that should have been provided to you.
7. Select the date range you wish to run the script over
8. A chrome window should pop up, with coral and then MYLE open. Log into each.
9. In the command prompt, you'll see a list of questionnaires with either a :white_check_mark: for completed or an :x: for failed.
10. You'll be given the option to re-run the failed ones - try that once or twice, if there's one that consistently fails, do it manually.
