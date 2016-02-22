PACKAGE = mgarepo
VERSION = 1.11.10
.PHONY: all $(DIRS) clean

clean:
	# TODO



# rules to build tarball

dist: tar
tar:
	git archive --prefix $(PACKAGE)-$(VERSION)/ HEAD | xz -9 > $(PACKAGE)-$(VERSION).tar.xz
