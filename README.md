# Document Management Integration System

DMIS (Document Management Integration System) is a dynamic application allowing orginisation to connect multiple repository hosting services (currently ingegrated with GitHub, GitLab, Confluence, SharePoint and SMB). User authentication is handled through SSO, using any OAuth2-compatible Identity Provider.

A showcase of basic system functionality can be seen in the video below:

<p align="center">
  <a href="https://youtu.be/9-a6aLzqZM4">
    <img 
      src="https://img.youtube.com/vi/9-a6aLzqZM4/maxresdefault.jpg" 
      alt="Watch the video" 
      width="800"
    >
  </a>
</p>


## System documentation

Full system documentation can be found [here](documentation/SYSTEM_DOCUMENTATION.md).

## Setup instructions

Full system setup instructions can be found [here](documentation/SETUP_INSTRUCTIONS.md).

## Developer instructions

Firstly, it is recommended to add your SSH keys to Github, [this guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) can be followed.

### Step 1 (This should only be done at initial setup)

Then clone the repository

    $ git clone git@github.com:Studentprojekt-KCL/document_management_system.git

If you write code in python, create a virtual env and install tox:

    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ pip install tox

### Step 2 (This should be done for each commit)

Check out a new branch (where feature name references the issue fixed):

    $ git checkout -b feature/<FEATURE_NAME>

If a python package (pyproject.toml) file exists for the microservice you are developing:

    $ pip install -e src/<YOUR_MICROSERVICE>

To install all the dependencies.

The new code can now be constructed! After completing the issue, run the linters locally:

    $ tox

Once linters and unit tests passes in tox, do:

    $ git add <FILE>

Where \<FILE\> refers to all files changed and created.

Now, do:

    $ git commit -S -m "<COMMIT MESSAGE> (ref #<TICKET_ID>)"

(Only use -S to sign the commit if you have set up a GPG key in Github).

And finally, push the commit:

    $ git push --set-upstream origin <BRANCH_NAME>

Once the commit is complete and it either has been merged into develop or you want to continue with another commit:

    $ git checkout develop
    $ git pull
