**Installation**

- Install python from https://www.python.org/downloads/
- Install git from https://git-scm.com/downloads. Instructions available [here](https://www.linode.com/docs/development/version-control/how-to-install-git-on-linux-mac-and-windows/)
- Create a new directory for this project 
- Open the command line or terminal
- Go into the repository directory
- Clone the repository 

```
git clone https://github.com/hernandezrivera/rw-content-counter.git
```
- Install pip. _Depending on your installation and OS, you can try different commands. Anyway, the newest python version should come with pip pre-installed._

 - Windows
```
python -m pip install
```
 - MacOS
```
sudo easy_install pip
```

- Check that you are in the project directory where you find ``requirements.txt`` and ``main.py``. To check type ``ls`` (MacOS) or ``dir`` (Windows) 
 
- Get the dependencies: 
```
pip3 install -r .\requirements
```
- Run the script 
```
python3 main.py
```
- In a browser, go to the URL provided on the console (typically http://127.0.0.1:5000), specify the parameters of your query, Submit the query and wait for the results.

- After the execution, you will see on your browser a table with the Inoreader folders and tags. You will have also CSV and JSON files with more detailed datasets, that you can use to perform your own analysis, such as items per inoreader source, matches with ReliefWeb ...
