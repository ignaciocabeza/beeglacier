# BeeGlacier

This is an  application for managing Amazon Glacier Storage made with Beeware.git

## Dowload

Sorry, the app is in development and it's not available for download as a `.dmg` or as an `.app`

### List of vaults

![App](https://i.ibb.co/3dXVCcH/Screenshot-2020-02-14-at-11-49-57.png "BeeGlacier")

### Vault files

![App](https://i.ibb.co/Hqx8bYz/Screenshot-2020-02-14-at-11-50-14.png "BeeGlacier")

### Credentials configuration

![App](https://i.ibb.co/84rtS7H/Screenshot-2020-02-14-at-11-50-26.png "BeeGlacier")

## Setup Environment

Create a python virtual enviroment
```
pip install -r requirements.txt (for development)
```
```
briefcase dev
```

## Features
- List vaults
- Create Vault
- Remove Vault
- Upload File to Vault
- List Archives of a Vault
- Start an inventory job to request the list of archives of a Vault
- Download an archive
- Delete Archive

## To-do (In the future)

- [ ] [Download Archive] Select type of download when you start a archive donwload job
- [ ] [System Wide] Show how much cost($) each action (Download, Upload, etc)
- [ ] [System Wide] Flake8
- [ ] [Download Archive] Create confirm dialog before creating a Archive download Job

## Beeware

This cross-platform app was generated by Briefcase The BeeWare Project:
- `Briefcase`: https://github.com/beeware/briefcase
- `The BeeWare Project`: https://beeware.org/
- `Becoming a financial member of BeeWare`: https://beeware.org/contributing/membership
