import github

from MgaRepo import Error, config

class GitHub(object):
    def __init__(self, username = config.get("github", "login"), password = config.get("github", "password")):
        print("username: %s password: %s" % (username, password))
        self.github = github.Github(login_or_token=username, password=password)
        self.organization = self.github.get_organization(config.get("github", "organization", "mdkcauldron"))
        self.repos = self.organization.get_repos()
