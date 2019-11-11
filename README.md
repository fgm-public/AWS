# AWS
**This repository contains projects which developed for deploying to Amazon web services public cloud.**

## Ethical disclaimer
> In this application, we work with the portal and API of the headhunter.ru company. We are very grateful to headhunter.ru company for the beautiful portal and excellently-designed well-documented API, programming with which was a pure pleasure. We are aware of the complexity of the development and maintenance of such services and such a business as a whole. We are also fully aware that specialized databases are one of the main assets of the company. In connection with the foregoing, we should in no case forget that **this application was created exclusively for educational purposes and completely excludes the possibility of any business use.** Also remember that the company itself provides analytical reporting services that you can always use and this will be the best choice.

## Repository structure
The root of the repository contains two directories: 

* **local**
* **cloud**

### local directory
> Contains code which intended to run in a local environment for testing purposes

### cloud directory
> Contains code which intended to run in a cloud environment for production purposes

## Naming conventions
All code is contained into directories which names consist of the **proper name itself** and **after-dash suffix** correspond with AWS services names.
For example:

*analyze-lambda*

where *analyze* is the name of application and *lamba* is the name of AWS service.

## Secrets
All secrets, passwords, authentication, authorization keys an so on, stored in **'credentials.py'** files which added to *.gitinore* for convenience's sake. Instead of this file, there is its fake double, named **'creds.py'** which contains the same content with bulk secret strings to provide a way for file structure clarification. Therefore,  after cloning this repo, change all 'creds.py' names to 'credentials.py'.
>Or replace python imports:

    from creds import a, b, c
Then, fill these files with your own secrets.  

## Requirements
All requirements stored in **requirements.txt**, which may be installed using:

    shell> pip install -r requirements.txt
for the local environment, or

    shell> pip install -r requirements.txt -t .\destination 
for the cloud environment.
