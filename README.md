# VIBE / ニュース

### News for people who like japanese theme.

## Requirements 

    fastapi
    uvicorn
    requests
    python-multipart
    python-dotenv
    Pillow

  the above requirements need to be installed -> preferably in requirements.txt file

## Installation

   Step 1 - clone the repo.

      git clone https://github.com/RitamRoa/VIBE.git

  Step 2 - install requirements.

       pip install -r requirements.txt 

  Step 3 - get your key from newsapi.org.

       in your .env file upload your newsapi.org api key -> NEWS_API_KEY: 12342456. 

  Step 4 - intialize your virtual env i.e. .venv 

       python -m venv .venv 
       .\/.venv/Scripts/Activate.ps1

  Step 5 - Lets run the app 

       .\.venv/Scripts/python -m uvicorn main:app --reload host 0.0.0.0 --port 8000 



  VIBE / ニュース should now be working at localhost:8000 

  ~ made with ❤️ by roa for you

  if you want to contribute please fork this repository and make a CONTRIBUTING.md file and send a PR. The PR will be thoroughly reviewed within 24-48 hours.
       

   
