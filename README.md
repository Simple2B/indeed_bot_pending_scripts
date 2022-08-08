## Instruction

1. [Go to](https://console.cloud.google.com/cloud-resource-manager "Visit page")
2. Click "Create Project"
3. Enter project name
4. [Go to](https://console.cloud.google.com/apis/credentials "Go to")
5. Click "Create Credentials"
6. Click "OAuth client ID"
7. Click "External"
8. Set "Application Type" -> "Desctop Application"
9. Click "Create"
10. In modal window click "Download JSON"
11. Rename downloaded fite to "gmail_account.json"
12. Put this file to the project folder
13. [Go to](https://console.cloud.google.com/apis/credentials "Go to")
14. Select your project
15. Click "Create Credentials"
16. Click "Service Account"
17. Enter service account name
18. Click "Done"
19. [Go to](https://console.cloud.google.com/iam-admin/serviceaccounts "Go to")
20. Copy you service account email
21. Grant access to folder with spreadsheets and clients spreadsheets for copied email
22. Go to your service account settings page
23. Open "Keys" tab
24. Click "Add key"
25. Click "Create new key"
26. Click "JSON"
27. Click "Create"
28. Rename downloaded fite to "service_account.json"
29. Put this file to the project folder
30. [Go to](https://console.cloud.google.com/apis/library "Go to")
31. Search each of APIs and enable it

    - Gmail API
    - Google Drive API
    - Google Sheets API

32. Create account on [this site](https://anti-captcha.com/ "this site")
33. Charge your balance
34. [Go to](https://anti-captcha.com/clients/settings/apisetup "Go to")
35. Copy your API key
36. Paste your API key in step 37

37. In project folder rename file "sample.env" > ".env"
    If you dont have code. Go to step 38. After receiving the code, follow steps 40 - 49
38. Open ".env" file
39. Set your values for each variable
    Example:
    `SERVICE_ACCOUNT_EMAIL=acc-1-25593@emmanuel-352612.iam.gserviceaccount.com`
    `INDEED_MAIN_SPREADSHEET_ID=1Y-36LyvSze_Zf5m8851dbHvLjcpgk9R6923h1h_Z4ocfTno`
    `ANTI_CAPTCHA_KEY=787c4e664312516123348a223c775d9a06649b`

INDEED_MAIN_SPREADSHEET_ID you can find in spreadsheet url:
docs.google.com/spreadsheets/d/**1SbcEAAhF2PWIGKZMOJupn\_\_jkTGigWtmAqWlrHZri3Q**/edit#gid=1107219298

40. Install GitHub on your PC
41. [Go to project repository](https://github.com/Simple2B/indeed_bot "Go to")
42. Click "Code"
43. Click "Download ZIP" or skip this step
    Step 42 is easier to download the code, but for updates you should always visit github and download the zip. The next steps look difficult, but in the future you will run only one command to update the code (`git pull`)
44. Click "HTTP"(or SSH, if [configured](https://www.theserverside.com/blog/Coffee-Talk-Java-News-Stories-and-Opinions/GitHub-SSH-Windows-Example "configured"))
45. Copy url(use this url in step 45)
46. Open project destination folder
47. Click right mouse button
48. Click "Open git bash in this folder"
49. Run command `git clone <repository url (step 41)>`

50. Install [Python 3.9](https://www.python.org/downloads/ "Python 3.9")
51. In project folder create and activate [virtual environment](https://docs.python.org/3/library/venv.html "virtual environment")
52. Install dependencies (`pip install -r requirements_to_freeze.txt`)
53. Run `python -m app`
54. The first time it starts, it should automatically open the google auth page (if not, copy the URL in the terminal). On this page, you need to be authenticated in Gmail, which you will use to forward 2FA emails.
55. Enter Batch
56. Click "OK"
