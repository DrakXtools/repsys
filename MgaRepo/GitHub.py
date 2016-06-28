from MgaRepo import Error, config
from MgaRepo.rpmutil import detectVCS, get_pkg_tag
from MgaRepo.layout import package_name, remove_current
from MgaRepo.git import GIT
from MgaRepo.svn import SVN
import github
from rpm import RPMTAG_SUMMARY, RPMTAG_URL

class GitHub(object):
    def __init__(self, username = config.get("github", "login"), password = config.get("github", "password")):
        self._github = github.Github(login_or_token=username, password=password)
        self._organization = self._github.get_organization(config.get("github", "organization", "mdkcauldron"))
        self._repos = self._organization.get_repos()

    def repository_exists(self, name):
        for repo in self._repos:
            if repo.name == name:
                return repo
        return None

    def create_repository(self, pkgname, **kwargs):
        repository = self._organization.create_repo(pkgname, **kwargs)
        return repository

    # workaround pygithub bug
    @staticmethod
    def __get_stats_commit_activity(self):
        """
        :calls: `GET /repos/:owner/:repo/stats/commit_activity <developer.github.com/v3/repos/statistics/#get-the-number-of-commits-per-hour-in-each-day>`_
        :rtype: None or list of :class:`github.StatsCommitActivity.StatsCommitActivity`
        """
        headers, data = self._requester.requestJsonAndCheck(
                "GET",
                self.url + "/stats/commit_activity"
                )
        if data == None:
            return None
        else:
            return [
                    github.StatsCommitActivity.StatsCommitActivity(self._requester, headers, attributes, completed=True)
                    for attributes in data
                    ]

    def import_package(self, target):
        vcs = detectVCS(target)
        top_dir = vcs.get_topdir()
        info = vcs.info2(top_dir)
        pkgname = package_name(remove_current(info["URL"]))

        repository = self.repository_exists(pkgname)
        #if not repository or repository.get_stats_commit_activity() is None:
        if not repository or self.__get_stats_commit_activity(repository) is None:
            if not repository:
                summary = get_pkg_tag(RPMTAG_SUMMARY, path=top_dir)
                url = get_pkg_tag(RPMTAG_URL, path=top_dir)
                repository = self.create_repository(pkgname, description=summary, homepage=url)
                print("GitHub repository created at " + repository.html_url)
            else:
                print("Empty GitHub repository already created at %s, using" % repository.html_url)

            if isinstance(vcs, GIT):
                status, output = vcs.remote("add", repository.full_name, repository.ssh_url, noerror=True)
                if status:
                    if status == 128 and ("fatal: remote %s already exists." % repository.full_name) \
                            in output:
                                pass
                    else:
                        raise Error(output)

                status, output = vcs.push(repository.full_name, "master", show=True)
                if status == 0:
                    print("Success!")
                    return True
        else:
            raise Error("GitHub repository already exists at " + repository.html_url)
        raise Error("GitHub import failed...")
