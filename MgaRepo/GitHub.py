from MgaRepo import Error, config
from MgaRepo.rpmutil import detectVCS, get_pkg_tag, clone
from MgaRepo import layout
from MgaRepo.git import GIT
from MgaRepo.svn import SVN
from rpm import RPMTAG_SUMMARY, RPMTAG_URL
import github
import os

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

    def delete_repository(self, pkgname, **kwargs):
        repository = self.repository_exists(pkgname)
        if repository:
            print("deleting repository %s" % repository.full_name)
            repository.delete()
            return True
        raise Error("repository %s doesn't exist!" % (self._organization.login+"/"+pkgname))

    def import_package(self, target):
        if not os.path.exists(target):
            target = layout.checkout_url(layout.package_url(target))
        vcs = detectVCS(target)
        top_dir = vcs.get_topdir()
        pkgname = layout.package_name(layout.remove_current(vcs.url))

        repository = self.repository_exists(pkgname)
        if not repository or not repository.get_stats_commit_activity():
            if not repository:
                if os.path.exists(vcs.path):
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
            elif isinstance(vcs, SVN):
                clone(vcs.url, bindownload=False)
                return self.import_package(pkgname)

        else:
            raise Error("GitHub repository already exists at " + repository.html_url)
        raise Error("GitHub import failed...")
