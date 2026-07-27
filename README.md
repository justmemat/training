# OSF Training App

## Windows setup

Open Command Prompt in the application directory and install the required packages
with the same Python interpreter used to run the application:

```bat
python -m pip install -r requirements.txt
```

Then start the application:

```bat
python main.py
```

If `python` is not recognized, use the Windows Python launcher instead:

```bat
py -m pip install -r requirements.txt
py main.py
```

The PDF-generation feature requires `pypdf`. Installing `requirements.txt` installs
both Flet and pypdf and is preferred over installing packages one at a time.
