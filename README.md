# Getting Started
The Red Eye system is a Python based application using the Flask framework for the backend and Bootstrap 5.10 for the front end. The production server is running Python 3.9.5 and testing is done using Pythong 3.9.13.

## Prerequisites
### Visual Studio Code
VS Code is recommened as this repository includes launch tasks for initializing the database and running the server but any IDE can be used. VS Code can be downloaded [HERE](https://code.visualstudio.com/download).

### Python
Python 3.9 is recommended. If on Windows this can be easily installed using the Windows store and searching for Python or clicking [THIS](https://www.microsoft.com/store/productId/9P7QFQMJRFP7) link.

### Git
Git is required for source control and can be found [HERE](https://git-scm.com/downloads). The default installation settings are fine.

## Setup
### Cloning the Repository
Once all of the prerequisites have been met you will need to clone the repository. To do this you will need to open file explorer and navigate to the folder where you'd like to store the source code. Once there click inside of the top address bar to the right of any text. This should highligh the text and allow you to type. Type ***powershell*** and press enter. This will open a PowerShell window in that directory. Now run the following command.

`git clone https://gitlab.com/cs4912/2203-red.git`

This will clone the repository into that directory and you should now see a folder called ***teamred***.
### VS Code and Python
If you chose to add right click items for VS Code during installation you can simply right click on the folder and select ***Open with Code***. You can also open VS Code and select ***Open Folder***.

Once VS Code opens you will want to open a Python file such as ***app.py*** to let VS Code know that we will be working with Python files.

Next press ``CTRL + ` `` to open a terminal at the bottom of VS Code. You will need to run the following command inside of this terminal.

`python -m venv env`

This will create a new Python virtual environment which will be used to isolate the libraries used by this application. Once you do this you should see a popup on the bottom right asking if you want to switch to this virtual environment. Select yes. To fully activate the new virtual environment you will need to close the current terminal and open a new one. You can do this by clicking the trash can icon at the top right of the terminal window which will close the current terminal. Then use ``CTRL + ` `` to open a new one using the new virtual environment. You will know that the virtual environment is active if you see text that says ***(env)*** before the normal command line text. 

Next we need to install the libraries. The list of required libraries is stored in the ***requirements.txt*** file in the repository. To install all of the libraries automatically just run the following command.

`python -m pip install -r requirements.txt`

### Initialize Database
To keep things simple we will use a file based database called SQLite. This means all of the data for the system will reside in a single file. Before we can run the application locally we will need to create this database file. This can be done using the ***init_db.py*** file located in the root of the repository. If using VS Code you can select the ***Run and Debug*** tab on the left. This is the tab with the play icon and a bug. Once that tab is selected there should be a ***Run and Debug*** dropdown menu at the top. From the dropdown select ***Init DB*** and click the green play icon. This will create the database file and then prompt you for information to create the first admin user. Enter whatever information you like and this will be what you use to log into the site locally. After the user has been created the script will automatically populate the database with a list of airports and then create a random list of planes used for simulating flight data.

If not using VS Code you can simply run `python init_db.py` from within any terminal to setup the DB.

Once the script is complete you should see an ***app.db*** file in the root of the repository. If any issues arise or you just want to start with a fresh database simply delete the file and repeat the above steps.

## Running the software
Navigate back to the ***Run and Debug*** tab and from the dropdown select ***App***. Simply click the play icon or press `F5` to start the webserver. The launch task will automatically open your default browser and navigate to the locally hosted server.