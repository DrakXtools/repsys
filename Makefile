PACKAGE = mgarepo
PKGVERSION = $(VERSION)
VERSION = 1.11.0
.PHONY: all $(DIRS) clean

clean:
	# TODO



# rules to build tarball

tar:
	git archive --prefix $(PACKAGE)-$(PKGVERSION)/ HEAD | xz -9 > $(PACKAGE)-$(PKGVERSION).tar.xz
