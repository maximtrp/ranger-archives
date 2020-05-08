RANGER_DIR=$(if $(XDG_CONFIG_HOME),$(XDG_CONFIG_HOME),$(HOME)/.config)/ranger
PLUGIN_DIR=$(RANGER_DIR)/plugins
RM ?= $(shell which rm)

BACKUP_LEVEL ?= simple


install:
	install -d $(PLUGIN_DIR)
	install --backup=$(BACKUP_LEVEL) compress.py $(PLUGIN_DIR)/compress.py
	install --backup=$(BACKUP_LEVEL) extract.py $(PLUGIN_DIR)/extract.py 

uninstall:
	$(RM) $(PLUGIN_DIR)/compress.py
	$(RM) $(PLUGIN_DIR)/extract.py
