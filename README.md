# AI-organiser-Discordbot

## Installing PostgreSQL

- [PostgreSQL](https://www.postgresql.org/download/) is required to run the bot. Follow the instructions on the website to install it on your system.
- After installation, create a new database and user for the bot. You can do this using the `psql` command line tool or a GUI tool like pgAdmin.
- by default, the database name is `taskdb`, the user is `taskbot`, and the password is `changeme`. You can change these values in the `config.env` file if you want.
- Make sure to create a `config.env` as `.env` file is ignored by git. You can use the `config.env.example` file as a template.

## Installing Python
- [Python](https://www.python.org/downloads/) is required to run the bot. Follow the instructions on the website to install it on your system.
- Make sure to install Python 3.11 or higher.
- You can check if Python is installed by running the following command in your terminal:
```bash
python --version
```
- Next set up a virtual environment to keep the dependencies isolated. You can do this by running the following command in your terminal:
```bash
python -m venv venv
```
- This will create a new directory called `venv` in your project folder. You can activate the virtual environment by running the following command:
```bash
# On Windows
venv\Scripts\activate
# On macOS and Linux
source venv/bin/activate
```
- Then install the required dependencies by running the following command:
```bash
pip install -r requirements.txt
```